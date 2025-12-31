"""
Sync Service - Order synchronization and normalization
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.models.integration import PlatformConfig, SyncJob
from app.models.order import OrderHeader, OrderItem
from app.integrations.base import NormalizedOrder, BasePlatformClient
from app.services import integration_service

logger = logging.getLogger(__name__)


class OrderSyncService:
    """
    Service for syncing orders from marketplace platforms
    """
    
    def __init__(self, db: Session):
        self.db = db
    
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
        
        # Create sync job record
        job = integration_service.create_sync_job(
            self.db,
            platform_config_id=str(config.id),
            job_type="POLL",
        )
        
        try:
            # Get platform client
            client = integration_service.get_client_for_config(config)
            
            # Default time range: last 24 hours
            if not time_from:
                time_from = datetime.utcnow() - timedelta(hours=24)
            if not time_to:
                time_to = datetime.utcnow()
            
            # Fetch orders with pagination
            cursor = None
            has_more = True
            
            while has_more:
                result = await client.get_orders(
                    time_from=time_from,
                    time_to=time_to,
                    cursor=cursor,
                    page_size=50,
                )
                
                orders = result.get("orders", [])
                cursor = result.get("next_cursor")
                has_more = result.get("has_more", False) and cursor
                
                # Process each order
                for raw_order in orders:
                    stats["fetched"] += 1
                    
                    try:
                        # Get order details if needed
                        order_id = self._extract_order_id(config.platform, raw_order)
                        if order_id:
                            detail = await client.get_order_detail(order_id)
                            if detail:
                                raw_order = detail
                        
                        # Normalize order
                        normalized = client.normalize_order(raw_order)
                        
                        # Process order (create or update)
                        created, updated = self._process_order(normalized)
                        
                        if created:
                            stats["created"] += 1
                        elif updated:
                            stats["updated"] += 1
                        else:
                            stats["skipped"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing order: {e}")
                        stats["errors"] += 1
            
            # Update last sync time
            config.last_sync_at = datetime.utcnow()
            self.db.commit()
            
            # Complete sync job
            integration_service.complete_sync_job(
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
            
        except Exception as e:
            logger.error(f"Sync failed for {config.platform}/{config.shop_name}: {e}")
            integration_service.complete_sync_job(
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
            return raw_order.get("id")
        return None
    
    def _process_order(self, normalized: NormalizedOrder) -> Tuple[bool, bool]:
        """
        Process normalized order - create or update in database
        Returns: (created, updated)
        """
        # Check if order already exists (idempotent)
        existing = self.db.query(OrderHeader).filter(
            and_(
                OrderHeader.channel_order_no == normalized.platform_order_id,
                OrderHeader.channel_code == normalized.platform,
            )
        ).first()
        
        if existing:
            # Update existing order
            return self._update_order(existing, normalized)
        else:
            # Create new order
            return self._create_order(normalized)
    
    def _create_order(self, normalized: NormalizedOrder) -> Tuple[bool, bool]:
        """Create new order from normalized data"""
        order = OrderHeader(
            channel_code=normalized.platform,
            channel_order_no=normalized.platform_order_id,
            
            customer_name=normalized.customer_name,
            customer_phone=normalized.customer_phone,
            customer_email=normalized.customer_email,
            
            shipping_name=normalized.shipping_name,
            shipping_phone=normalized.shipping_phone,
            shipping_address=normalized.shipping_address,
            shipping_district=normalized.shipping_district,
            shipping_city=normalized.shipping_city,
            shipping_province=normalized.shipping_province,
            shipping_postal=normalized.shipping_postal_code,
            
            status_raw=normalized.order_status,
            status_normalized=normalized.status_normalized,
            
            subtotal=normalized.subtotal,
            shipping_fee=normalized.shipping_fee,
            discount_amount=normalized.discount_amount,
            total_amount=normalized.total_amount,
            
            payment_method=normalized.payment_method,
            paid_at=normalized.paid_at,
            
            shipping_method=normalized.shipping_method,
            tracking_no=normalized.tracking_number,
            courier=normalized.courier,
            
            order_date=normalized.order_created_at or datetime.utcnow(),
            
            raw_payload=normalized.raw_payload,
        )
        
        self.db.add(order)
        self.db.flush()
        
        # Create order items
        for idx, item_data in enumerate(normalized.items):
            item = OrderItem(
                order_id=order.id,
                line_no=idx + 1,
                sku=item_data.get("sku", ""),
                product_name=item_data.get("product_name", ""),
                qty=item_data.get("quantity", 1),
                unit_price=item_data.get("unit_price", 0),
                line_total=item_data.get("total_price", 0),
                discount_amount=item_data.get("discount_amount", 0),
            )
            self.db.add(item)
        
        self.db.commit()
        
        logger.info(f"Created order: {normalized.platform}/{normalized.platform_order_id}")
        return (True, False)
    
    def _update_order(
        self,
        existing: OrderHeader,
        normalized: NormalizedOrder,
    ) -> Tuple[bool, bool]:
        """Update existing order if status changed"""
        # Only update if status changed
        if existing.status_normalized == normalized.status_normalized:
            return (False, False)
        
        # Update status
        existing.status_raw = normalized.order_status
        existing.status_normalized = normalized.status_normalized
        
        # Update tracking info if available
        if normalized.tracking_number:
            existing.tracking_no = normalized.tracking_number
        if normalized.courier:
            existing.courier = normalized.courier
        if normalized.paid_at:
            existing.paid_at = normalized.paid_at
        
        # Update raw payload
        existing.raw_payload = normalized.raw_payload
        
        self.db.commit()
        
        logger.info(
            f"Updated order: {normalized.platform}/{normalized.platform_order_id} "
            f"-> {normalized.status_normalized}"
        )
        return (False, True)
    
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
        # Get platform config
        config = self.db.query(PlatformConfig).filter(
            and_(
                PlatformConfig.platform == platform,
                PlatformConfig.is_active == True,
            )
        ).first()
        
        if not config:
            logger.warning(f"No active config found for platform: {platform}")
            return (False, False)
        
        # Get platform client
        client = integration_service.get_client_for_config(config)
        
        # Fetch order details
        raw_order = await client.get_order_detail(order_id)
        if not raw_order:
            logger.warning(f"Order not found: {platform}/{order_id}")
            return (False, False)
        
        # Normalize and process
        normalized = client.normalize_order(raw_order)
        return self._process_order(normalized)


async def sync_all_platforms(db: Session) -> Dict[str, Dict]:
    """
    Sync orders from all active platform configurations
    """
    service = OrderSyncService(db)
    results = {}
    
    # Get all active configs with sync enabled
    configs = integration_service.get_platform_configs(db, is_active=True)
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
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise ValueError(f"Platform config not found: {config_id}")
    
    service = OrderSyncService(db)
    return await service.sync_platform_orders(config, time_from, time_to)
