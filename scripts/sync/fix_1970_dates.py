
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_1970_dates():
    db = SessionLocal()
    try:
        # Find orders with invalid dates
        # Use a safe threshold, e.g., before 2024 (project start)
        invalid_orders = db.query(OrderHeader).filter(
            OrderHeader.shipped_at < '2024-01-01'
        ).all()
        
        total = len(invalid_orders)
        logger.info(f"Found {total} orders with invalid dates (< 2024).")
        
        if total == 0:
            return

        # Group by platform to reuse clients
        orders_by_platform = {}
        for o in invalid_orders:
            orders_by_platform.setdefault(o.channel_code, []).append(o)
            
        for platform, orders in orders_by_platform.items():
            logger.info(f"Processing {len(orders)} orders for {platform}...")
            
            # Get Config
            config = db.query(PlatformConfig).filter(
                PlatformConfig.platform == platform, 
                PlatformConfig.is_active == True
            ).first()
            
            if not config:
                logger.error(f"No active config for {platform}. Skipping.")
                continue
                
            # Init Client
            client = None
            if platform == 'tiktok':
                client = TikTokClient(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    shop_id=config.shop_id,
                    access_token=config.access_token,
                    refresh_token=config.refresh_token
                )
            # Add other platforms if needed, but error was mostly TikTok
            
            if not client:
                 logger.warning(f"Client init failed for {platform}")
                 continue

            # Process in batches
            batch_size = 50
            sem = asyncio.Semaphore(10)
            
            async def process_batch(batch_orders):
                async with sem:
                    try:
                        ids = [o.external_order_id for o in batch_orders]
                        details = await client.get_order_details_batch(ids)
                        
                        updates_map = {}
                        for d in details:
                             oid = d.get("id")
                             # TikTok API v2 usually returns seconds (10 digits) or ms (13 digits)
                             # get_order_details_batch -> _make_request -> returns dict
                             # We need to handle both.
                             # If we see 1970 again, it means we divided seconds by 1000.
                             
                             # Let's check raw values
                             # collection_time, rts_time, update_time
                             
                             ut = d.get("collection_time") or d.get("rts_time") or d.get("update_time")
                             if oid and ut:
                                 updates_map[oid] = ut
                        
                        local_fixed = 0
                        for order in batch_orders:
                            raw_ts = updates_map.get(order.external_order_id)
                            if raw_ts:
                                # Smart Conversion Logic
                                ts = int(raw_ts)
                                # If ts is in milliseconds (13 digits, > 10^11), divide by 1000
                                if ts > 100000000000: 
                                    ts = ts / 1000
                                
                                new_date = datetime.fromtimestamp(ts, tz=timezone.utc)
                                
                                # Verification
                                if new_date.year < 2024:
                                    logger.warning(f"⚠️ Still getting old date for {order.external_order_id}: {new_date} (raw: {raw_ts})")
                                else:
                                    order.shipped_at = new_date
                                    local_fixed += 1
                        
                        db.commit()
                        if local_fixed > 0:
                            logger.info(f"Fixed {local_fixed} orders.")
                            
                    except Exception as e:
                        logger.error(f"Batch failed: {e}")
                        db.rollback()

            tasks = []
            for i in range(0, len(orders), batch_size):
                batch = orders[i:i+batch_size]
                tasks.append(process_batch(batch))
            
            await asyncio.gather(*tasks)
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_1970_dates())
