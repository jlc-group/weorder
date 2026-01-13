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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backfill_fix")

DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

async def get_client(db, platform):
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
    return client

async def fix_single_order(db, client, order_pk, external_id, platform):
    try:
        shipped_at = None
        
        if platform == 'tiktok':
            detail_list = await client.get_order_details_batch([external_id])
            if detail_list:
                detail = detail_list[0]
                collection_time = detail.get("collection_time")
                rts_time = detail.get("rts_time")
                update_time = detail.get("update_time")
                
                ts = 0
                if collection_time and int(collection_time) > 0:
                    ts = int(collection_time)
                elif rts_time and int(rts_time) > 0:
                    ts = int(rts_time)
                # elif update_time: # For this fix, strict shipping time preferred? Or update time OK?
                #     ts = int(update_time)
                
                if ts > 0:
                    # FIX LOGIC
                    if ts > 10000000000: 
                        shipped_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                    else:
                        shipped_at = datetime.fromtimestamp(ts, tz=timezone.utc)
        
        if shipped_at:
            # Ensure it's not 1970
            if shipped_at.year < 2000:
                logger.warning(f"Order {external_id} still resolved to {shipped_at}. Skipping update.")
                return False
                
            db.execute(
                text("UPDATE order_header SET shipped_at = :dt WHERE id = :pk"),
                {"dt": shipped_at, "pk": order_pk}
            )
            logger.info(f"Fixed {external_id}: {shipped_at}")
            return True
        else:
            logger.warning(f"Could not determine ship date for {external_id}")
            
    except Exception as e:
        logger.error(f"Error {platform} {external_id}: {e}")
        return False
    return False

async def main():
    logger.info("Starting Optimized 1970 Date Fix (Concurrent)...")
    
    db = SessionLocal()
    
    # Cache client
    client = await get_client(db, 'tiktok') 
    if not client:
        logger.error("No TikTok client available")
        return

    # Semaphore for concurrency
    sem = asyncio.Semaphore(20) # 20 concurrent requests

    async def sem_task(pk, ext_id, channel):
        async with sem:
            return await fix_single_order(db, client, pk, ext_id, channel)

    with engine.connect() as conn:
        # Find broken orders
        logger.info("Querying broken orders...")
        # Use streaming result or fetchmany if too large, but 120k is okay-ish for list of tuples
        rows = conn.execute(text("""
            SELECT id, channel_code, external_order_id
            FROM order_header
            WHERE status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
            AND shipped_at < '2000-01-01'
        """)).fetchall()
        
        count = len(rows)
        logger.info(f"Found {count} orders with 1970 dates.")
        
        tasks = []
        for r in rows:
            pk, channel, ext_id = r
            if channel != 'tiktok': 
                continue
            tasks.append(sem_task(pk, ext_id, channel))
            
        logger.info(f"Created {len(tasks)} tasks. Starting execution...")
        
        # Process in chunks to avoid memory explosion of tasks/results
        chunk_size = 1000
        total_fixed = 0
        
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i + chunk_size]
            results = await asyncio.gather(*chunk)
            fixed_in_chunk = sum(1 for r in results if r)
            total_fixed += fixed_in_chunk
            logger.info(f"Processed chunk {i}-{i+len(chunk)}. Fixed: {fixed_in_chunk}. Total: {total_fixed}/{count}")
            db.commit() # Commit every chunk
                
        logger.info(f"Done. Fixed {total_fixed}/{count} orders.")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
