import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from app.core import SessionLocal
from app.models import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient
from app.integrations.shopee import ShopeeClient
from app.integrations.lazada import LazadaClient

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backfill_full.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backfill_full")

DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

async def get_client(db, platform, config_cache):
    if platform in config_cache:
        return config_cache[platform]
    
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == platform, PlatformConfig.is_active == True).first()
    if not config:
        return None
        
    client = None
    if platform == 'tiktok':
        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
    elif platform == 'shopee':
        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
    elif platform == 'lazada':
        client = LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
    if client:
        config_cache[platform] = client
    return client

async def process_batch(batch, config_cache):
    db = SessionLocal()
    updated_count = 0
    
    try:
        tasks = []
        for order_id, platform, external_id in batch:
            try:
                client = await get_client(db, platform, config_cache)
                if not client:
                    continue
                tasks.append(process_single_order(db, client, order_id, external_id, platform))
            except Exception as e:
                logger.error(f"Setup error {external_id}: {e}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if res and not isinstance(res, Exception):
                updated_count += 1
                
        db.commit()
        return updated_count
    except Exception as e:
        logger.error(f"Batch error: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

async def process_single_order(db, client, order_pk, external_id, platform):
    try:
        shipped_at = None
        
        if platform == 'tiktok':
            # Batch optimization possible but keeping simple for mixed types
            # Actually TikTok supports batch detail but let's do single for simplicity across platforms
            # Or use list? No, verify correctness 1-by-1
            # We need to replicate the priority logic: collection_time > rts_time > update_time
            # But client.get_order_detail returns raw dict.
            # Wait, client.get_order_detail is generic.
            # We can use client.get_orders([ids]) logic if available?
            # TikTokClient has get_order_details_batch.
            detail_list = await client.get_order_details_batch([external_id])
            if detail_list:
                detail = detail_list[0]
                # Logic from normalize_order
                collection_time = detail.get("collection_time")
                rts_time = detail.get("rts_time")
                update_time = detail.get("update_time")
                
                ts = 0
                if collection_time and int(collection_time) > 0:
                    ts = int(collection_time)
                elif rts_time and int(rts_time) > 0:
                    ts = int(rts_time)
                elif update_time:
                    ts = int(update_time)
                
                if ts > 0:
                    # Fix 1970 bug: If ts is already in seconds (e.g. 1735...), don't divide.
                    # 10,000,000,000 seconds is year 2286. 
                    # 1,000,000,000 seconds is year 2001.
                    # 1,000,000,000,000 milliseconds is year 2001.
                    if ts > 10000000000: 
                        # Assume milliseconds
                        shipped_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                    else:
                        # Assume seconds
                        shipped_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        elif platform == 'shopee':
            detail = await client.get_order_detail(external_id)
            if detail:
                pickup_time = detail.get("pickup_done_time")
                update_time = detail.get("update_time")
                
                ts = 0
                if pickup_time and int(pickup_time) > 0:
                    ts = int(pickup_time)
                elif update_time:
                    ts = int(update_time)
                
                if ts > 0:
                    shipped_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        elif platform == 'lazada':
            detail = await client.get_order_detail(external_id)
            if detail:
                updated_at_str = detail.get("updated_at")
                if updated_at_str:
                    # Parse "2025-12-31 10:26:46 +0700"
                    # Simplified hack
                    dt_part = updated_at_str.split(" +")[0]
                    # Assume +0700
                    from datetime import timedelta
                    shipped_at = datetime.strptime(dt_part, "%Y-%m-%d %H:%M:%S") - timedelta(hours=7)
                    shipped_at = shipped_at.replace(tzinfo=timezone.utc)

        if shipped_at:
            # Direct update via SQL for speed/thread-safety in this context
            db.execute(
                text("UPDATE order_header SET shipped_at = :dt WHERE id = :pk"),
                {"dt": shipped_at, "pk": order_pk}
            )
            return True
            
    except Exception as e:
        logger.error(f"Error {platform} {external_id}: {e}")
        return False
    return False

async def main():
    logger.info("Starting Full Backfill...")
    
    # Cache clients
    config_cache = {}
    
    # connection
    with engine.connect() as conn:
        # Get count
        count = conn.execute(text("""
            SELECT count(*) FROM order_header 
            WHERE status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
            AND shipped_at IS NULL
        """)).scalar()
        logger.info(f"Total orders to backfill: {count}")
        
        # Cursor pagination logic
        offset = 0
        batch_size = 50
        
        # Parallel workers
        sem = asyncio.Semaphore(10) 
        
        while offset < count + 1000: # safety margin
             # Fetch batch
             rows = conn.execute(text(f"""
                SELECT id, channel_code, external_order_id
                FROM order_header
                WHERE status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
                AND shipped_at IS NULL
                LIMIT {batch_size}
             """)).fetchall()
             
             if not rows:
                 break
                 
             # Process
             batch_param = [(r[0], r[1], r[2]) for r in rows]
             
             # Run batch
             updated = await process_batch(batch_param, config_cache)
             
             logger.info(f"Processed batch. Updated {updated}/{len(rows)}. Remaining approx {count - offset}")
             offset += len(rows)
             # Wait a bit
             await asyncio.sleep(0.5)

    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(main())
