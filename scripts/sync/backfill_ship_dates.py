"""
Backfill Ship Dates from TikTok API

This script fetches the true 'update_time' from TikTok API for orders
that are SHIPPED/DELIVERED but missing 'shipped_at'.

This ensures the Daily Outbound report reflects the actual shipping date,
not the sync date.

Run: python scripts/sync/backfill_ship_dates.py
"""
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

sys.path.append(os.getcwd())

print("Imports started...", flush=True)

from sqlalchemy import text
from app.core import SessionLocal
from app.models import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient
from app.integrations.shopee import ShopeeClient
from app.integrations.lazada import LazadaClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def backfill_dates():
    # Setup CLI args
    import argparse
    parser = argparse.ArgumentParser(description='Backfill Ship Dates')
    parser.add_argument('--days', type=int, default=30, help='Days to look back')
    parser.add_argument('--platform', type=str, default='tiktok', help='Platform to backfill')
    parser.add_argument('--all', action='store_true', help='Process ALL orders in range, not just missing shipped_at')
    args = parser.parse_args()

    print("Starting logic...", flush=True)
    db = SessionLocal()
    try:
        # 1. Get configs
        query = db.query(PlatformConfig).filter(PlatformConfig.is_active == True)
        if args.platform:
            query = query.filter(PlatformConfig.platform == args.platform)
            
        configs = query.all()
        
        if not configs:
            logger.error(f"No active config found for {args.platform}.")
            return

        for config in configs:
            logger.info(f"Processing {config.platform} - {config.shop_name}")
            
            # Manually create client
            client = None
            if config.platform == 'tiktok':
                client = TikTokClient(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    shop_id=config.shop_id,
                    access_token=config.access_token,
                    refresh_token=config.refresh_token
                )
            elif config.platform == 'shopee':
                client = ShopeeClient(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    shop_id=config.shop_id,
                    access_token=config.access_token,
                    refresh_token=config.refresh_token
                )
            elif config.platform == 'lazada':
                client = LazadaClient(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    shop_id=config.shop_id,
                    access_token=config.access_token,
                    refresh_token=config.refresh_token
                )
            else:
                logger.warning(f"Backfill not implemented for {config.platform}")
                continue
            
            # 2. Find orders to update
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=args.days)
            
            logger.info(f"Fetching orders from {start_date.date()} to {end_date.date()}...")
            
            # Base query
            q = db.query(OrderHeader).filter(
                OrderHeader.channel_code == config.platform,
                OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'RETURNED']),
                OrderHeader.updated_at >= start_date,
                OrderHeader.updated_at <= end_date
            )
            
            # If not --all, only find those missing shipped_at
            if not args.all:
                q = q.filter(OrderHeader.shipped_at.is_(None))
                
            orders = q.order_by(OrderHeader.updated_at.desc()).all()
            
            total = len(orders)
            logger.info(f"Found {total} orders to backfill.")
            
            if total == 0:
                continue
            
            # 3. Process in batches with High Concurrency
            batch_size = 50
            concurrency = 10  # Process 10 batches in parallel
            sem = asyncio.Semaphore(concurrency)
            
            async def process_batch(batch_idx, batch_orders):
                async with sem:
                    try:
                        order_ids = [o.external_order_id for o in batch_orders]
                        
                        updates_map = {}
                        
                        if config.platform == 'lazada':
                            # Lazada has no batch API, must loop concurrently within batch?? 
                            # Or just loop sequentially since this is already running in parallel with other batches?
                            # Let's loop sequentially for simplicity here as we have 10 concurrent batches.
                            for o_id in order_ids:
                                try:
                                    detail = await client.get_order_detail(o_id)
                                    # Normalize logic manual extraction
                                    # updated_at is generic, but for Shipped/Delivered order, it implies shipping time.
                                    raw_date = detail.get("updated_at")
                                    if raw_date:
                                        # Parse ISO
                                        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                                        updates_map[o_id] = dt.timestamp()
                                except Exception as e:
                                    logger.error(f"Lazada fetch error {o_id}: {e}")
                        
                        else:
                            # TikTok / Shopee use batch
                            details = await client.get_order_details_batch(order_ids)
                            for d in details:
                                 # TikTok uses 'id', Shopee uses 'order_sn'
                                 oid = d.get("id") or d.get("order_sn")
                                 
                                 # STRICT: Only use collection_time (TikTok) or pickup_done_time (Shopee)
                                 final_time = d.get("collection_time") or d.get("pickup_done_time")
                                 updates_map[oid] = final_time
                        
                        local_updated = 0
                        for order in batch_orders:
                            ut = updates_map.get(order.external_order_id)
                            
                            new_shipped_at = None
                            if ut and ut > 0:
                                # Auto-detect MS vs Seconds (Year 3000 check)
                                if ut > 32503680000: # Year 3000 in seconds
                                     ut = ut / 1000
                                new_shipped_at = datetime.fromtimestamp(ut, tz=timezone.utc)
                            
                            # Update if changed (including clearing it to None)
                            if order.shipped_at != new_shipped_at:
                                order.shipped_at = new_shipped_at
                                local_updated += 1
                                
                        # Commit per batch (safe in single-threaded asyncio)
                        db.commit()
                        if local_updated > 0:
                            logger.info(f"✅ Batch {batch_idx}: Updated {local_updated}/{len(batch_orders)}")
                        return local_updated
                        
                    except Exception as e:
                        logger.error(f"❌ Batch {batch_idx} Failed: {e}")
                        db.rollback() 
                        return 0
    
            logger.info(f"🚀 Starting Turbo Mode: {concurrency} workers...")
            
            tasks = []
            for i in range(0, total, batch_size):
                batch = orders[i:i+batch_size]
                tasks.append(process_batch(i // batch_size, batch))
                
            results = await asyncio.gather(*tasks)
            total_updated = sum(results)
                    
            logger.info(f"✨ Backfill Complete for {config.shop_name}! Updated {total_updated}/{total} orders.")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(backfill_dates())
