"""
Sync Service - Order synchronization and normalization
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from starlette.concurrency import run_in_threadpool
import logging
import asyncio

logger = logging.getLogger(__name__)

from app.models.integration import PlatformConfig, SyncJob
from app.models.order import OrderHeader, OrderItem
# Check if company model import is needed, usually assuming it's available or importing it
from app.models.master import Company
from app.integrations.base import NormalizedOrder, BasePlatformClient
from . import integration_service


class OrderSyncService:
    """
    Service for syncing orders from marketplace platforms
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _extract_timestamp(self, payload: dict, key: str) -> Optional[datetime]:
        """Extract Unix timestamp from raw_payload and convert to datetime"""
        if not payload:
            return None
        try:
            ts = payload.get(key)
            if ts and int(ts) > 0:
                return datetime.fromtimestamp(int(ts))
        except (ValueError, TypeError):
            pass
        return None
    
    def _extract_decimal(self, payload: dict, *keys) -> Optional[float]:
        """Extract nested decimal value from raw_payload (e.g., 'payment', 'original_shipping_fee')"""
        if not payload:
            return None
        try:
            val = payload
            for k in keys:
                val = val.get(k, {}) if isinstance(val, dict) else None
                if val is None:
                    return None
            return float(val) if val else 0
        except (ValueError, TypeError):
            return 0
    
    async def sync_platform_orders(
        self,
        config: PlatformConfig,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Sync orders from a single platform configuration
        Returns: {fetched, created, updated, skipped}
        """
        stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }
        
        # Get default company (Blocking)
        company = await run_in_threadpool(lambda: self.db.query(Company).first())
        if not company:
            logger.error("No company found in database. Cannot sync orders.")
            raise Exception("No company found")
        company_id = company.id
        
        # Create sync job record (Blocking)
        job = await run_in_threadpool(
            integration_service.create_sync_job,
            self.db,
            platform_config_id=str(config.id),
            job_type="POLL",
        )
        
        try:
            # Get platform client
            client = integration_service.get_client_for_config(config)
            
            # Default time range: last 7 days (covers older orders still pending)
            if not time_from:
                time_from = datetime.utcnow() - timedelta(days=7)
            if not time_to:
                time_to = datetime.utcnow()
            
            # Fetch orders with pagination
            cursor = None
            has_more = True
            
            # Determine status filters based on platform
            # For TikTok: fetch multiple statuses that need packing
            # TikTok API supports one status per request, so we loop
            status_filters = []
            if config.platform == 'tiktok':
                # Statuses that need attention/packing
                status_filters = ['AWAITING_SHIPMENT', 'UNPAID', 'ON_HOLD', 'AWAITING_COLLECTION']
            elif config.platform == 'shopee':
                status_filters = ['READY_TO_SHIP', 'PROCESSED']
            elif config.platform == 'lazada':
                status_filters = ['pending', 'ready_to_ship']
            else:
                status_filters = [None]  # No filter
            
            # Loop through each status filter
            for status_filter in status_filters:
                cursor = None
                has_more = True
                
                while has_more:
                    # Async IO
                    result = await client.get_orders(
                        time_from=time_from,
                        time_to=time_to,
                        status=status_filter,
                        cursor=cursor,
                        page_size=50,
                    )
                    
                    orders = result.get("orders", [])
                    cursor = result.get("next_cursor")
                    has_more = result.get("has_more", False) and cursor
                    
                    # Process orders in batches (Chunk size 50)
                    # This drastically reduces API calls for platforms requiring detail fetch (e.g. Shopee)
                    chunk_size = 50
                    for i in range(0, len(orders), chunk_size):
                        batch = orders[i:i+chunk_size]
                        batch_ids = []
                        
                        # 1. Collect IDs that need detail fetching
                        for raw in batch:
                            order_id = self._extract_order_id(config.platform, raw)
                            if order_id:
                                batch_ids.append(order_id)
                        
                        # 2. Batch Fetch Details (if supported)
                        detailed_batch = []
                        if hasattr(client, 'get_order_details_batch'):
                            try:
                                logger.info(f"Using Batch Fetch for {len(batch_ids)} orders")
                                # Async IO - Batch Call
                                detailed_batch = await client.get_order_details_batch(batch_ids)
                            except Exception as e:
                                logger.error(f"Batch fetch error: {e}, falling back to single fetch")
                                detailed_batch = []
                        else:
                            logger.info("Client does not support get_order_details_batch")
                        
                        # 3. Fallback / Merge Logic
                        # If batch fetch returned results, use them. Otherwise use original raw (and fetch single if needed)
                        # For Shopee: batch fetch returns full details.
                        # For others: might overwrite completely.
                        
                        final_batch = detailed_batch if detailed_batch else batch
                        
                        # If batch fetch failed or returned fewer items (unlikely but possible), 
                        # we should ideally fallback to single fetch, but for now let's process what we have.
                        # Mapping back is tricky if order isn't preserved, but platforms usually return list.
                        
                        # 4. Process Batch
                        for raw_order in final_batch:
                            stats["fetched"] += 1
                            
                            try:
                                # If we didn't get detail from batch (and batch logic wasn't used/failed),
                                # try single fetch for platforms that need it (Fallback)
                                if not detailed_batch and hasattr(client, 'get_order_detail'):
                                    order_id = self._extract_order_id(config.platform, raw_order)
                                    if order_id:
                                        detail = await client.get_order_detail(order_id)
                                        if detail:
                                            raw_order = detail

                                # Normalize order (Fast, CPU bound but okay)
                                normalized = client.normalize_order(raw_order)
                                
                                # Process order (Blocking DB)
                                created, updated = await run_in_threadpool(
                                    self._process_order, normalized, company_id
                                )
                                
                                if created:
                                    stats["created"] += 1
                                elif updated:
                                    stats["updated"] += 1
                                else:
                                    stats["skipped"] += 1
                                
                            except Exception as e:
                                logger.error(f"Error processing order: {e}")
                                stats["errors"] += 1
            
            # Update last sync time (Blocking)
            config.last_sync_at = datetime.utcnow()
            await run_in_threadpool(self.db.commit)
            
            # Complete sync job (Blocking)
            await run_in_threadpool(
                integration_service.complete_sync_job,
                self.db,
                job_id=str(job.id),
                orders_fetched=stats["fetched"],
                orders_created=stats["created"],
                orders_updated=stats["updated"],
                orders_skipped=stats["skipped"],
            )
            
            logger.info(
                f"Sync completed for {config.platform}/{config.shop_name}: "
                f"fetched={stats['fetched']}, created={stats['created']}, "
                f"updated={stats['updated']}, skipped={stats['skipped']}"
            )
            # TikTok Specific: Sync Returns/Cancellations
            if config.platform == "tiktok":
                try:
                    return_stats = await self.sync_returns(config, time_from, time_to)
                    stats["updated"] += return_stats.get("updated", 0)
                    stats["fetched"] += return_stats.get("fetched", 0)
                except Exception as re:
                    logger.error(f"Error syncing TikTok returns: {re}")

        except Exception as e:
            logger.error(f"Sync failed for {config.platform}/{config.shop_name}: {e}")
            await run_in_threadpool(
                integration_service.complete_sync_job,
                self.db,
                job_id=str(job.id),
                error_message=str(e),
            )
            raise
        
        return stats
    
    def _extract_order_id(self, platform: str, raw_order: Dict) -> Optional[str]:
        """Extract order ID from raw order data"""
        if platform == "shopee":
            return raw_order.get("order_sn")
        elif platform == "lazada":
            return str(raw_order.get("order_id", ""))
        elif platform == "tiktok":
            # TikTok search returns full details, no need to fetch again
            return None
        return None
    
    def _process_order(self, normalized: NormalizedOrder, company_id: Any) -> Tuple[bool, bool]:
        """
        Process normalized order - create or update in database
        Returns: (created, updated)
        """
        # Check if order already exists (idempotent)
        existing = self.db.query(OrderHeader).filter(
            and_(
                OrderHeader.external_order_id == normalized.platform_order_id,
                OrderHeader.channel_code == normalized.platform,
            )
        ).first()
        
        if existing:
            # Update existing order
            return self._update_order(existing, normalized)
        else:
            # Create new order
            return self._create_order(normalized, company_id)
    
    def _create_order(self, normalized: NormalizedOrder, company_id: Any) -> Tuple[bool, bool]:
        """Create new order from normalized data"""
        # Construct full address
        address_parts = [
            normalized.shipping_address,
            normalized.shipping_district,
            normalized.shipping_city,
            normalized.shipping_province,
            normalized.shipping_postal_code,
            normalized.shipping_country
        ]
        full_address = " ".join([p for p in address_parts if p])

        order = OrderHeader(
            company_id=company_id,
            channel_code=normalized.platform,
            external_order_id=normalized.platform_order_id,
            
            customer_name=normalized.customer_name,
            customer_phone=normalized.customer_phone,
            # Map shipping address to customer_address
            customer_address=full_address,
            
            status_raw=normalized.order_status,
            status_normalized=normalized.status_normalized,
            
            # Amount mapping
            subtotal_amount=normalized.subtotal,
            shipping_fee=normalized.shipping_fee,
            discount_amount=normalized.discount_amount,
            total_amount=normalized.total_amount,
            
            payment_method=normalized.payment_method,
            # paid_at not in model
            
            shipping_method=normalized.shipping_method,
            # Field name mapping
            tracking_number=normalized.tracking_number,
            courier_code=normalized.courier,
            
            # shipped_at: ONLY set if platform provides actual pickup/collection time
            # Do NOT use fallback (order_updated_at) as it's inaccurate for Daily Outbound
            shipped_at=normalized.shipped_at,
            order_datetime=normalized.order_created_at or datetime.utcnow(),
            
            raw_payload=normalized.raw_payload,
            
            # New fields extracted from raw_payload
            rts_time=self._extract_timestamp(normalized.raw_payload, 'rts_time'),
            paid_time=self._extract_timestamp(normalized.raw_payload, 'paid_time'),
            delivery_time=self._extract_timestamp(normalized.raw_payload, 'delivery_time'),
            collection_time=self._extract_timestamp(normalized.raw_payload, 'collection_time'),
            original_shipping_fee=self._extract_decimal(normalized.raw_payload, 'payment', 'original_shipping_fee'),
            shipping_fee_platform_discount=self._extract_decimal(normalized.raw_payload, 'payment', 'shipping_fee_platform_discount'),
            is_cod=normalized.raw_payload.get('is_cod', False) if normalized.raw_payload else False,
        )
        
        self.db.add(order)
        self.db.flush()
        
        # Create order items
        for idx, item_data in enumerate(normalized.items):
            item = OrderItem(
                order_id=order.id,
                # line_no not in model, removing
                sku=item_data.get("sku", ""),
                product_name=item_data.get("product_name", ""),
                quantity=item_data.get("quantity", 1),
                unit_price=item_data.get("unit_price", 0),
                line_total=item_data.get("total_price", 0),
                line_discount=item_data.get("discount_amount", 0),
                original_price=item_data.get("original_price", 0),
                platform_discount=item_data.get("platform_discount", 0),
                seller_discount=item_data.get("seller_discount", 0),
            )
            self.db.add(item)
        
        # Auto-create InvoiceProfile if invoice_data present (from Shopee/Lazada)
        self._auto_create_invoice_profile(order, normalized.raw_payload)
        
        self.db.commit()
        
        # Check if new order is already RTS (e.g. initial sync of old orders or missed webhook)
        if order.status_normalized == "READY_TO_SHIP":
            if not order.rts_time:
                order.rts_time = datetime.utcnow()
                self.db.commit()
            
            from app.services.stock_service import StockService
            try:
                StockService.process_order_deduction(self.db, order)
                logger.info(f"Triggered initial Stock Deduction for RTS order {order.external_order_id}")
            except Exception as e:
                logger.error(f"Failed to deduct stock for {order.external_order_id}: {e}")

        logger.info(f"Created order: {normalized.platform}/{normalized.platform_order_id}")
        return (True, False)
    
    def _update_order(
        self,
        existing: OrderHeader,
        normalized: NormalizedOrder,
    ) -> Tuple[bool, bool]:
        """Update existing order if status changed or data missing"""
        updated = False
        
        # 1. Update status if changed
        # GUARD: Don't downgrade from terminal states (RETURNED, CANCELLED)
        status_changed = False
        if existing.status_normalized != normalized.status_normalized:
            if existing.status_normalized in ["RETURNED", "CANCELLED"]:
                # Check if normalized status is ALSO a terminal state, otherwise skip status update
                if normalized.status_normalized not in ["RETURNED", "CANCELLED"]:
                    logger.info(f"Skipping status update for terminal order {existing.external_order_id}: {existing.status_normalized} -> {normalized.status_normalized}")
                else:
                    existing.status_raw = normalized.order_status
                    existing.status_normalized = normalized.status_normalized
                    status_changed = True
                    updated = True
            else:
                existing.status_raw = normalized.order_status
                existing.status_normalized = normalized.status_normalized
                status_changed = True
                updated = True

        if status_changed:
            
            # TRIGGER STOCK DEDUCTION IF STATUS BECOMES READY_TO_SHIP
            if normalized.status_normalized == "READY_TO_SHIP":
                if not existing.rts_time:
                    existing.rts_time = datetime.utcnow()
                    updated = True
                
                from app.services.stock_service import StockService
                try:
                    StockService.process_order_deduction(self.db, existing)
                    logger.info(f"Triggered Stock Deduction for RTS order {existing.external_order_id}")
                except Exception as e:
                    logger.error(f"Failed to deduct stock for {existing.external_order_id}: {e}")

        # 2. Update tracking info if missing or changed
        if normalized.tracking_number and existing.tracking_number != normalized.tracking_number:
            existing.tracking_number = normalized.tracking_number
            updated = True
        if normalized.courier and existing.courier_code != normalized.courier:
            existing.courier_code = normalized.courier
            updated = True
        
        # 3. Update raw payload (always update to get latest data)
        if existing.raw_payload != normalized.raw_payload:
            existing.raw_payload = normalized.raw_payload
            updated = True
        
        # 4. Update shipped_at if platform provides actual pickup time OR status changed to shipped
        if normalized.status_normalized in ["SHIPPED", "DELIVERED"]:
            if normalized.shipped_at and existing.shipped_at != normalized.shipped_at:
                existing.shipped_at = normalized.shipped_at
                updated = True
            elif existing.shipped_at is None:
                # Fallback to current time if we just detected it's shipped but platform didn't give a time
                existing.shipped_at = datetime.utcnow()
                updated = True
        
        # 5. Check for missing items and add them if available
        # This is critical for Lazada where search API doesn't return items
        from sqlalchemy import func
        item_count = self.db.query(func.count(OrderItem.id)).filter(OrderItem.order_id == existing.id).scalar() or 0
        if item_count == 0 and normalized.items:
            for item_data in normalized.items:
                item = OrderItem(
                    order_id=existing.id,
                    sku=item_data.get("sku", ""),
                    product_name=item_data.get("product_name", ""),
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data.get("unit_price", 0),
                    line_total=item_data.get("total_price", 0),
                    line_discount=item_data.get("discount_amount", 0),
                    original_price=item_data.get("original_price", 0),
                    platform_discount=item_data.get("platform_discount", 0),
                    seller_discount=item_data.get("seller_discount", 0),
                )
                self.db.add(item)
            updated = True

        # 6. Update timestamps from raw_payload
        raw = normalized.raw_payload or {}
        
        # TikTok: collection_time comes directly
        if normalized.platform == "tiktok":
            collection_ts = self._extract_timestamp(raw, 'collection_time')
            if collection_ts and existing.collection_time != collection_ts:
                existing.collection_time = collection_ts
                updated = True
        
        # Shopee: use pickup_done_time as collection_time
        elif normalized.platform == "shopee":
            pickup_ts = self._extract_timestamp(raw, 'pickup_done_time')
            if pickup_ts and existing.collection_time != pickup_ts:
                existing.collection_time = pickup_ts
                updated = True
        
        # Update other timestamps if not set
        if not existing.rts_time:
            rts_ts = self._extract_timestamp(raw, 'rts_time')
            if rts_ts:
                existing.rts_time = rts_ts
                updated = True
        
        if not existing.paid_time:
            paid_ts = self._extract_timestamp(raw, 'paid_time') or self._extract_timestamp(raw, 'pay_time')
            if paid_ts:
                existing.paid_time = paid_ts
                updated = True
                
        if not existing.delivery_time:
            delivery_ts = self._extract_timestamp(raw, 'delivery_time')
            if delivery_ts:
                existing.delivery_time = delivery_ts
                updated = True

        if updated:
            self.db.commit()
            logger.info(
                f"Updated order data: {normalized.platform}/{normalized.platform_order_id} "
                f"(Status: {normalized.status_normalized})"
            )
            return (False, True)
            
        return (False, False)

    
    def _auto_create_invoice_profile(self, order: OrderHeader, raw_payload: Dict[str, Any]) -> None:
        """
        Auto-create InvoiceProfile if order contains invoice_data from platform.
        Supports: Shopee (invoice_data field), Lazada (tax_code/branch_number fields)
        """
        from app.models.invoice import InvoiceProfile
        from datetime import datetime
        
        if not raw_payload:
            return
        
        invoice_data = None
        source = "PLATFORM_SYNC"
        platform = order.channel_code.upper() if order.channel_code else "UNKNOWN"
        
        # Shopee: invoice_data field
        if raw_payload.get("invoice_data"):
            invoice_data = raw_payload.get("invoice_data")
            logger.info(f"Found invoice_data from Shopee for order {order.external_order_id}")
        
        # Lazada: tax_code and branch_number fields
        elif raw_payload.get("tax_code") and raw_payload.get("tax_code") not in ["lazada", "shopee", "tiktok"]:
            invoice_data = {
                "tax_id": raw_payload.get("tax_code"),
                "branch": raw_payload.get("branch_number", "00000"),
                "invoice_name": order.customer_name,
                "platform": "lazada"
            }
            logger.info(f"Found tax_code from Lazada for order {order.external_order_id}")
        
        if not invoice_data:
            return
        
        # Check if InvoiceProfile already exists for this order
        existing = self.db.query(InvoiceProfile).filter(
            InvoiceProfile.order_id == order.id
        ).first()
        
        if existing:
            logger.debug(f"InvoiceProfile already exists for order {order.external_order_id}")
            return
        
        try:
            # Extract fields from invoice_data
            # Shopee format: {number, series_number, info: {name, address, tax_code, ...}}
            info = invoice_data.get("info", invoice_data)
            
            profile = InvoiceProfile(
                order_id=order.id,
                profile_type="COMPANY" if info.get("tax_code") or info.get("tax_id") else "PERSONAL",
                invoice_name=(info.get("name") or info.get("invoice_name") or order.customer_name)[:200],
                tax_id=(info.get("tax_code") or info.get("tax_id") or "")[:20].strip(),
                branch=(str(info.get("branch") or "00000"))[:50].strip(),
                address_line1=info.get("address") or order.customer_address,
                phone=info.get("phone") or order.customer_phone,
                email=info.get("email"),
                status="PENDING",
                created_source=source,
                # Store raw platform data
                platform_invoice_data={
                    "platform": platform,
                    "raw_data": invoice_data,
                    "order_sn": order.external_order_id
                },
                platform_synced_at=datetime.utcnow()
            )
            
            self.db.add(profile)
            logger.info(f"Auto-created InvoiceProfile for order {order.external_order_id} from {platform} (tax_id: {profile.tax_id})")
            
        except Exception as e:
            logger.error(f"Failed to auto-create InvoiceProfile for order {order.external_order_id}: {e}")
    
    
    async def process_webhook_order(
        self,
        platform: str,
        order_id: str,
        event_type: str,
    ) -> Tuple[bool, bool]:
        """
        Process order from webhook event
        Returns: (created, updated)
        """
        # Get platform config (Blocking)
        config = await run_in_threadpool(
            lambda: self.db.query(PlatformConfig).filter(
                and_(
                    PlatformConfig.platform == platform,
                    PlatformConfig.is_active == True,
                )
            ).first()
        )
        
        if not config:
            logger.warning(f"No active config found for platform: {platform}")
            return (False, False)
        
        # Get platform client
        client = integration_service.get_client_for_config(config)
        
        # Fetch order details (Async IO)
        raw_order = await client.get_order_detail(order_id)
        if not raw_order:
            logger.warning(f"Order not found: {platform}/{order_id}")
            return (False, False)
        
        # Normalize and process
        normalized = client.normalize_order(raw_order)
        
        # Need company_id for creating order (Blocking)
        company = await run_in_threadpool(lambda: self.db.query(Company).first())
        if not company:
            return (False, False)
            
        # Process order (Blocking)
        return await run_in_threadpool(self._process_order, normalized, company.id)

    async def sync_returns(self, config: PlatformConfig, time_from: datetime, time_to: datetime) -> Dict[str, int]:
        """
        Sync returns/reverse orders (Specific for TikTok)
        """
        stats = {"fetched": 0, "updated": 0}
        
        if config.platform != "tiktok":
            return stats
            
        try:
            client = integration_service.get_client_for_config(config)
            # Check if client has get_reverse_orders
            if not hasattr(client, "get_reverse_orders"):
                return stats

            cursor = None
            has_more = True
            
            while has_more:
                resp = await client.get_reverse_orders(time_from, time_to, cursor)
                if not resp:
                    break
                    
                returns_list = resp.get("returns", []) 
                
                cursor = resp.get("next_page_token")
                has_more = bool(cursor)
                
                for ret in returns_list:
                    stats["fetched"] += 1
                    order_id = ret.get("order_id")
                    
                    if order_id:
                        # Find Order
                        order = self.db.query(OrderHeader).filter(
                            OrderHeader.external_order_id == order_id
                        ).first()
                        
                        if order and order.status_normalized not in ["RETURNED", "TO_RETURN", "CANCELLED", "DELIVERY_FAILED"]:
                            tiktok_status = ret.get('return_status', 'UNKNOWN')
                            return_type = ret.get('return_type', 'UNKNOWN')
                            return_reason = ret.get('return_reason', '')
                            
                            # If it's a cancellation, set to CANCELLED
                            if "CANCEL" in tiktok_status:
                                order.status_normalized = "CANCELLED"
                                order.status_raw = f"REVERSE_{tiktok_status}"
                                stats["updated"] += 1
                            # DELIVERY_FAILED: Customer didn't receive parcel (product coming back)
                            elif "not_received" in return_reason:
                                order.status_normalized = "DELIVERY_FAILED"
                                order.status_raw = f"REVERSE_{tiktok_status}"
                                stats["updated"] += 1
                            # Physical return (product coming back) -> TO_RETURN
                            elif return_type == "RETURN_AND_REFUND":
                                order.status_normalized = "TO_RETURN"
                                order.status_raw = f"REVERSE_{tiktok_status}"
                                stats["updated"] += 1
                            # Refund only (no product return) -> RETURNED
                            else:
                                order.status_normalized = "RETURNED"
                                order.status_raw = f"REVERSE_{tiktok_status}"
                                stats["updated"] += 1
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error syncing returns for {config.platform}: {e}")
            
        return stats


async def sync_all_platforms(db: Session) -> Dict[str, Dict]:
    """
    Sync orders from all active platform configurations
    """
    service = OrderSyncService(db)
    results = {}
    
    # Get all active configs with sync enabled (Blocking)
    configs = await run_in_threadpool(
        lambda: integration_service.get_platform_configs(db, is_active=True)
    )
    configs = [c for c in configs if c.sync_enabled]
    
    for config in configs:
        key = f"{config.platform}_{config.shop_id}"
        try:
            stats = await service.sync_platform_orders(config)
            results[key] = {"status": "success", **stats}
        except Exception as e:
            results[key] = {"status": "error", "error": str(e)}
    
    return results


async def sync_single_platform(
    db: Session,
    config_id: str,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
) -> Dict[str, int]:
    """
    Sync orders from a single platform configuration
    """
    # Get config (Blocking)
    config = await run_in_threadpool(integration_service.get_platform_config, db, config_id)
    if not config:
        raise ValueError(f"Platform config not found: {config_id}")
    
    service = OrderSyncService(db)
    return await service.sync_platform_orders(config, time_from, time_to)
