import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.finance import MarketplaceTransaction
from app.models.integration import PlatformConfig
from app.services import integration_service
from app.models.order import OrderHeader

logger = logging.getLogger(__name__)

class FinanceSyncService:
    def __init__(self, db: Session):
        self.db = db

    async def sync_platform_finance(
        self,
        config: PlatformConfig,
        time_from: datetime,
        time_to: datetime
    ) -> Dict[str, int]:
        """
        Sync financial data for a platform
        """
        client = integration_service.get_client_for_config(config)
        stats = {"fetched": 0, "created": 0, "errors": 0}

        try:
            if config.platform == "shopee":
                await self._sync_shopee_finance(client, config, time_from, time_to, stats)
            elif config.platform == "tiktok":
                await self._sync_tiktok_finance(client, config, time_from, time_to, stats)
            elif config.platform == "lazada":
                await self._sync_lazada_finance(client, config, time_from, time_to, stats)
            else:
                logger.warning(f"Finance sync not implemented for {config.platform}")
        
        except Exception as e:
            logger.error(f"Error syncing finance for {config.platform}: {e}")
            stats["errors"] += 1
            
        return stats

    async def _sync_shopee_finance(self, client, config, time_from, time_to, stats):
        """Sync Shopee Escrow Data (Optimized with Concurrency)"""
        import asyncio
        has_more = True
        page_no = 1
        page_size = 50
        sem = asyncio.Semaphore(20) # Limit concurrent requests

        # Helper to fetch with semaphore
        async def fetch_detail_safe(sn):
            async with sem:
                try:
                    return await client.get_escrow_detail(sn)
                except Exception as e:
                    logger.error(f"Failed to fetch detail for {sn}: {e}")
                    return None

        while has_more:
            # Fetch list
            resp = await client.get_escrow_list(time_from, time_to, page_size, page_no)
            if not resp:
                break
                
            escrow_list = resp.get("escrow_list", [])
            has_more = resp.get("more", False)
            page_no += 1
            
            if not escrow_list:
                continue

            # 1. OPTIMIZATION: Filter out already synced orders (Idempotency)
            order_sns = [item.get("order_sn") for item in escrow_list]
            
            # Check DB for existing transactions for these orders
            # We assume if we have "ITEM_PRICE" transaction for this order in "shopee", it's synced.
            # Or just check description containing the order_sn to be generic
            existing_sns = set()
            try:
                # Batch query is faster
                existing_q = self.db.query(MarketplaceTransaction.description).filter(
                    MarketplaceTransaction.platform == 'shopee',
                    MarketplaceTransaction.description.in_([f"{config.shop_name} - {sn}" for sn in order_sns])
                ).all()
                # Description format: "{shop_name} - {order_sn}"
                # Extract SN from description
                for row in existing_q:
                    desc = row.description
                    if " - " in desc:
                        sn_part = desc.split(" - ")[-1]
                        existing_sns.add(sn_part)
            except Exception as e:
                logger.warning(f"Failed to batch check existing Finance: {e}")

            # 2. Prepare tasks for missing
            tasks = []
            pending_items = []
            
            for item in escrow_list:
                order_sn = item.get("order_sn")
                if order_sn in existing_sns:
                    continue # Skip existing
                
                stats["fetched"] += 1
                tasks.append(fetch_detail_safe(order_sn))
                pending_items.append(item)
            
            if not tasks:
                logger.info(f"Skipped {len(escrow_list)} existing orders in batch.")
                continue

            # 3. Fetch concurrently
            logger.info(f"Fetching {len(tasks)} details concurrently...")
            results = await asyncio.gather(*tasks)
            
            # 4. Save results
            saved_count = 0
            for i, detail in enumerate(results):
                if detail:
                    self._save_shopee_transaction(detail, config, pending_items[i])
                    saved_count += 1
            
            stats["created"] += saved_count
            
            if not has_more:
                break

    async def _sync_tiktok_finance(self, client, config, time_from, time_to, stats):
        """Sync TikTok Statements and Transactions (Concurrent)"""
        import asyncio
        import time 

        cursor = None
        has_more = True
        all_statements = []
        
        # Step 1: Get All Statements first (usually small number)
        # Statements are daily/weekly summaries.
        while has_more:
            try:
                resp = await client.get_statements(time_from, time_to, cursor)
                if not resp:
                    break
                    
                statement_chunks = resp.get("statements", [])
                if statement_chunks:
                    all_statements.extend(statement_chunks)
                
                cursor = resp.get("next_page_token")
                has_more = bool(cursor)
            except Exception as e:
                logger.error(f"Error fetching tiktok statements: {e}")
                break
        
        if not all_statements:
            logger.info("No TikTok statements found in range.")
            return

        logger.info(f"Found {len(all_statements)} TikTok statements. Processing concurrently...")

        # Step 2: Process Statements Concurrently
        sem = asyncio.Semaphore(5) # Limit to 5 concurrent statements (intensive on DB/network)
        
        async def process_statement(statement):
            async with sem:
                statement_id = statement.get("id")
                
                # Check / Cleanup Existing
                # If we are syncing this statement, clearer to wipe existing transactions for this statement_id
                # so we don't duplicate.
                existing = self.db.query(MarketplaceTransaction).filter(
                    MarketplaceTransaction.platform == 'tiktok',
                    MarketplaceTransaction.payout_reference == statement_id
                ).delete()
                # Also delete the statement summary itself if exists
                # (We don't strictly have a separate table, just a tx with type STATEMENT_SUMMARY)
                # The delete above covers it if we use payout_reference consistenly.
                self.db.commit()
                
                # Save Statement Summary
                self._save_tiktok_statement(statement, config)
                stats["fetched"] += 1
                
                # Fetch Transactions (Pagination)
                tx_cursor = None
                tx_has_more = True
                tx_count = 0
                
                while tx_has_more:
                    try:
                        tx_resp = await client.get_statement_transactions(statement_id, tx_cursor)
                        if not tx_resp:
                            break
                        
                        transactions = tx_resp.get("statement_transactions", [])
                        if not transactions:
                            break
                            
                        # Bulk Insert Candidates
                        bulk_txs = []
                        
                        stmt_ts = statement.get("statement_time")
                        stmt_time = datetime.fromtimestamp(stmt_ts, timezone.utc) if stmt_ts else None

                        for tx_data in transactions:
                            tx_obj = self._prepare_tiktok_transaction(tx_data, config, statement_id, stmt_time)
                            if tx_obj:
                                bulk_txs.append(tx_obj)
                        
                        if bulk_txs:
                            # self.db.bulk_save_objects(bulk_txs) # Can be problematic with some session states
                            self.db.add_all(bulk_txs)
                            self.db.commit()
                            tx_count += len(bulk_txs)
                            stats["created"] += len(bulk_txs)
                            logger.info(f"Statement {statement_id}: Saved batch of {len(bulk_txs)} transactions.")
                        
                        tx_cursor = tx_resp.get("next_page_token")
                        tx_has_more = bool(tx_cursor)
                        
                        # Rate limit protection within loop
                        # await asyncio.sleep(0.1) 
                        
                    except Exception as e:
                        logger.error(f"Error processing statement {statement_id} page: {e}")
                        break
                
                logger.info(f"Statement {statement_id} done. {tx_count} txs synced.")

        # Create Tasks
        tasks = [process_statement(stmt) for stmt in all_statements]
        await asyncio.gather(*tasks)

    async def _sync_lazada_finance(self, client, config, time_from, time_to, stats):
        """Sync Lazada Transaction Details"""
        from dateutil.parser import parse

        try:
            # Lazada finance API is date-range based
            # We assume the range is reasonable (controlled by caller)
            transactions = await client.get_transaction_details(time_from, time_to)
            
            if not transactions:
                return

            logger.info(f"Found {len(transactions)} Lazada transactions.")
            
            # Simple deduplication could be added here if we had a reliable unique ID
            # For now, we append.
            
            for item in transactions:
                self._save_lazada_transaction(item, config)
                stats["fetched"] += 1
                stats["created"] += 1
                
        except Exception as e:
            logger.error(f"Error syncing lazada finance: {e}", exc_info=True)

    def _save_lazada_transaction(self, item: Dict, config: PlatformConfig):
        """Save Lazada Transaction"""
        from dateutil.parser import parse
        
        # Extract Fields
        order_no = item.get("order_no")
        # Some items might be general fees without order_no
        
        amount_val = item.get("amount") or 0
        amount = Decimal(str(amount_val))
        
        raw_tx_type = item.get("transaction_type") or "UNKNOWN"
        
        # Normalize transaction types for Lazada
        # Map payout-related types to ESCROW_RELEASE for เงินเข้าบัญชี calculation
        LAZADA_TX_TYPE_MAP = {
            # Payout types -> ESCROW_RELEASE
            "payout": "ESCROW_RELEASE",
            "payment": "ESCROW_RELEASE",
            "remittance": "ESCROW_RELEASE",
            "settlement": "ESCROW_RELEASE",
            "order_payment": "ESCROW_RELEASE",
            # Fee types -> Keep original or map to specific types
            "commission": "COMMISSION_FEE",
            "service_fee": "SERVICE_FEE",
            "shipping": "SHIPPING_FEE",
            "shipping_fee": "SHIPPING_FEE",
            "transaction_fee": "TRANSACTION_FEE",
            "adjustment": "ADJUSTMENT",
            # Revenue types
            "item_price": "ITEM_PRICE",
            "order": "ITEM_PRICE",
        }
        
        tx_type = LAZADA_TX_TYPE_MAP.get(raw_tx_type.lower(), raw_tx_type.upper())
        
        # Date
        date_str = item.get("transaction_date")
        try:
            if date_str:
                # Expecting format like "2025-01-01" or ISO
                tx_date = parse(date_str)
            else:
                tx_date = datetime.now()
        except:
            tx_date = datetime.now()

        # Link Order
        order_id = None
        if order_no:
            # Should optimize to avoid query per row if high volume
            # But Lazada usually returns fewer items than Shopee/TikTok per day?
            # Actually order items are individual lines.
            order = self.db.query(OrderHeader).filter(OrderHeader.external_order_id == str(order_no)).first()
            if order:
                order_id = order.id

        # Description
        details = item.get("details") or item.get("fee_name") or ""
        
        tx = MarketplaceTransaction(
            order_id=order_id,
            platform="lazada",
            transaction_type=tx_type,
            amount=amount,
            transaction_date=tx_date,
            description=f"{config.shop_name} - {details}",
            raw_data=item
        )
        self.db.add(tx)
        # Commit every row or batch?
        # Original code commits frequently. 
        self.db.commit()

    def _save_shopee_transaction(self, detail: Dict, config: PlatformConfig, summary: Dict):
        """Save Shopee Escrow Detail to DB"""
        order_sn = detail.get("order_sn")
        order_income = detail.get("order_income", {})
        
        # Resolve order_id
        order = self.db.query(OrderHeader).filter(OrderHeader.external_order_id == order_sn).first()
        order_id = order.id if order else None
        
        # Prepare Rows
        # Shopee structure: order_income -> items (price), seller_return_refund, cost_of_goods_sold, check keys
        # For simplify, we flatten "income_details" or similar keys
        
        # Example Shopee Detail (Structure assumption based on API):
        # items: [{model_name, original_price...}]
        # seller_rebate, commission_fee, service_fee, transaction_fee...
        
        # We assume standard keys: 
        # 'items': Income (Product Price)
        # 'buyer_paid_shipping_fee'
        # 'seller_transaction_fee', 'commission_fee', 'service_fee' (Expenses)
        # 'escrow_amount' (Net)
        
        tx_date = datetime.fromtimestamp(summary.get("escrow_release_time", 0)) if summary.get("escrow_release_time") else datetime.now()
        
        # Helper to insert
        def add_tx(tx_type, amount):
            if amount and float(amount) != 0:
                tx = MarketplaceTransaction(
                    order_id=order_id,
                    platform="shopee",
                    transaction_type=tx_type,
                    amount=Decimal(str(amount)),
                    transaction_date=tx_date,
                    payout_reference=None, # Shopee might not give batch ID easily in this API
                    description=f"{config.shop_name} - {order_sn}",
                    raw_data=detail
                )
                self.db.add(tx)

        # Map fields
        # Income
        add_tx("ITEM_PRICE", order_income.get("items_total_amount", 0)) # Verify key
        # Expenses (Negative? API usually gives positive value for fee, we should make it negative?)
        # Convention: Amount in DB should be signed. Income positive, Fee negative.
        # Shopee API usually returns Fee as positive number "10.00", so we must negate.
        
        # Check specific keys available in 'order_income'
        # Note: Without exact payload sample, I'll dump raw_data and parse major known keys
        
        # For now, simplistic approach:
        # If I can't guarantee keys, I should perhaps store the WHOLE detail as one record? 
        # No, user wants "Money Trail".
        
        # Known keys from Shopee V2:
        # cost_of_goods_sold, original_cost_of_goods_sold, seller_return_refund
        # voucher_from_seller, seller_coin_cash_back
        # shipping_fee_rebate, ...
        # transaction_fee, commission_fee, service_fee, ... drc_adjustable_refund
        
        # Expenses
        # Map known fee keys to negative values
        fee_mapping = {
            'transaction_fee': 'TRANSACTION_FEE',
            'commission_fee': 'COMMISSION_FEE',
            'service_fee': 'SERVICE_FEE', 
            'shipping_fee_paid_by_seller': 'SHIPPING_FEE',
            'shipping_fee_rebate': 'SHIPPING_REBATE', # This might be income? Usually rebate is +
            'voucher_from_seller': 'VOUCHER_CODE',
            'seller_coin_cash_back': 'COIN_CASHBACK_FEE',
            'payment_fee': 'PAYMENT_FEE',
            'drc_adjustable_refund': 'ADJUSTMENT'
        }

        for fee_key, tx_type in fee_mapping.items():
            val = order_income.get(fee_key)
            if val and float(val) != 0:
                amount = float(val)
                # Shopee API v2 usually returns fees as positive numbers e.g. "1.00"
                # We want Expense = Negative.
                # Except 'rebate' which is Income.
                
                if 'rebate' in fee_key:
                    add_tx(tx_type, abs(amount))
                else:
                    add_tx(tx_type, -abs(amount))
        
        # Income - Buyer Paid Shipping (Pass-through)
        buyer_shipping = order_income.get('buyer_paid_shipping_fee')
        if buyer_shipping and float(buyer_shipping) > 0:
             add_tx('SHIPPING_INCOME', float(buyer_shipping))

        # Core Income
        # Use cost_of_goods_sold (payout amount for items) if available, otherwise original_price
        deal_price = order_income.get("cost_of_goods_sold")
        original_price = order_income.get("original_cost_of_goods_sold")
        
        if deal_price and float(deal_price) != 0:
            add_tx("ITEM_PRICE", float(deal_price))
        elif original_price and float(original_price) != 0:
            add_tx("ITEM_PRICE", float(original_price))
        
        # ESCROW_RELEASE - Net payout amount (for "เงินเข้าบัญชี" calculation)
        # This is the actual amount that gets released to seller's wallet
        escrow_amount = summary.get("escrow_amount") or order_income.get("escrow_amount")
        if escrow_amount and float(escrow_amount) != 0:
            add_tx("ESCROW_RELEASE", float(escrow_amount))
            
        self.db.commit()

    def _save_tiktok_statement(self, statement: Dict, config: PlatformConfig):
        """Save TikTok Statement Summary"""
        # Statement fields: id, statement_time, settlement_amount, currency, payment_status
        statement_id = statement.get("id")
        settlement_amount = Decimal(str(statement.get("settlement_amount", 0)))
        currency = statement.get("currency", "THB")
        statement_time = datetime.fromtimestamp(statement.get("statement_time", 0))
        
        tx = MarketplaceTransaction(
            order_id=None,  # Statement is summary, no specific order
            platform="tiktok",
            transaction_type="STATEMENT_SUMMARY",
            amount=settlement_amount,
            currency=currency,
            transaction_date=statement_time,
            payout_reference=statement_id,
            description=f"{config.shop_name} - Statement {statement_id}",
            raw_data=statement
        )
        self.db.add(tx)
        self.db.commit()

    def _prepare_tiktok_transaction(self, transaction: Dict, config: PlatformConfig, statement_id: str = None, statement_time: datetime = None) -> MarketplaceTransaction:
        """Prepare TikTok Transaction Object (No Commit)"""
        # TikTok V2 uses 'settlement_amount' for the net value of the transaction.
        amount = Decimal(str(transaction.get("amount") or transaction.get("settlement_amount") or 0))
        currency = transaction.get("currency", "THB")
        tx_type = transaction.get("type", "UNKNOWN")
        
        # Date Logic
        from datetime import timezone
        
        tx_ts = transaction.get("order_create_time")
        if tx_ts:
            tx_date = datetime.fromtimestamp(tx_ts, timezone.utc)
        elif statement_time:
             tx_date = statement_time
        else:
             tx_date = datetime.now(timezone.utc)

        
        # Resolve order locally (cache could be optimized, but query is fast enough for now if indexed)
        # For bulk operations, resolving order_id for 1000 items one by one is slow.
        # Ideally we should pre-fetch map. But let's try direct first.
        
        external_id = transaction.get("order_id")
        # Optimization: We assume external_order_id is unique enough.
        # If we really need order_id integers, we should map.
        # But 'transaction' table usually links via order_id FK.
        # Let's do a subquery or just leave it nullable if not found?
        # A simple query per row is okay for batch of 20-50, but for thousands...
        
        # NOTE: For speed in bulk_save_objects, we might skip order_id lookup here if it's too slow 
        # or do a batch lookup before loop.
        # Let's do a single lookup for now.
        
        order_id = None
        if external_id:
            # This is synchronous blocking in async loop if not careful. 
            # But we are in a thread pool executor usually? No, this is async def called. 
            # DB operations here are blocking logic.
            # However `db.query` is fast.
            # To optimize: cache this lookup.
            pass

        # Since we are using bulk_save, we need the Order ID.
        # For now, let's just lookup. If performance is bad, we cache.
        
        if external_id:
             # Fast lookup match
             # We might want to use a cached map if we passed it in.
             # For now, simplistic.
             # WARNING: This `self.db` usage inside `async def` (via `process_statement`) 
             # without `await` is blocking the event loop.
             # But SQLAlchemy Session is not async. 
             # We should wrap this block in run_in_executor if we want true non-blocking.
             # Or just accept it's "concurrently blocking" threads? No, Python async is single thread.
             # So this blocks the loop.
             # For true async with sync DB, we need separate thread.
             
             # But practically, `await client` releases loop, then we crunch data (block), then await next.
             # It is "Interleaved", which is better than sequential network wait.
             
             existing_order_q = self.db.query(OrderHeader.id).filter(OrderHeader.external_order_id == external_id).first()
             if existing_order_q:
                 order_id = existing_order_q[0]

        return MarketplaceTransaction(
            order_id=order_id,
            platform="tiktok",
            transaction_type=tx_type,
            amount=amount,
            currency=currency,
            transaction_date=tx_date,
            payout_reference=statement_id,
            description=f"{config.shop_name} - {external_id or 'N/A'}",
            raw_data=transaction
        )

    def _save_tiktok_transaction(self, transaction: Dict, config: PlatformConfig, statement_id: str = None):
        """Legacy Wrapper"""
        obj = self._prepare_tiktok_transaction(transaction, config, statement_id)
        self.db.add(obj)
        self.db.commit()

