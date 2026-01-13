
import asyncio
import logging
import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.core import SessionLocal
from app.services import integration_service, sync_service

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smart_sync")

async def get_platform_total(client, config, start_date, end_date):
    """Get total count from Platform API"""
    try:
        if config.platform == 'tiktok':
            # TikTok Search API returns total
            resp = await client.get_orders(
                time_from=start_date, 
                time_to=end_date, 
                page_size=1
            )
            return resp.get("total", 0)
            
        elif config.platform == 'shopee':
            # Shopee get_order_list returns total
            resp = await client.get_orders(
                time_from=start_date, 
                time_to=end_date, 
                page_size=1
            )
            return resp.get("total", 0)
            
        elif config.platform == 'lazada':
             # Lazada get_orders returns countTotal
            resp = await client.get_orders(
                time_from=start_date, 
                time_to=end_date, 
                page_size=1
            )
            return resp.get("total", 0)
            
    except Exception as e:
        logger.error(f"Error getting total from {config.platform}: {e}")
        return -1
    return 0

def get_db_count(db, platform, start_date, end_date):
    """Get count from Local DB"""
    # Important: DB uses UTC if the driver converts, but checks are usually strict.
    # Our updated models use timezone=True, so we should be safe passing UTC datetimes.
    query = text("""
        SELECT count(*) FROM order_header 
        WHERE channel_code = :platform
        AND order_datetime >= :start
        AND order_datetime < :end
    """)
    result = db.execute(query, {
        "platform": platform, 
        "start": start_date, 
        "end": end_date
    }).scalar()
    return result

from app.integrations.tiktok import TikTokClient
from app.integrations.shopee import ShopeeClient
from app.integrations.lazada import LazadaClient

async def get_client_for_config(config):
    if config.platform == 'tiktok':
        return TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
    elif config.platform == 'shopee':
        return ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
    elif config.platform == 'lazada':
        return LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
    return None

async def smart_sync_platform(db, config, start_date, end_date, fix=False):
    logger.info(f"--- Smart Sync: {config.platform} ({start_date.date()} to {end_date.date()}) ---")
    
    sync_svc = sync_service.OrderSyncService(db)
    
    # Helper to get client
    client = await get_client_for_config(config)
    if not client:
        logger.error(f"Could not init client for {config.platform}")
        return

    # Inject client into sync_svc so we can use it
    # sync_svc.clients[config.platform] = client <-- This failed because clients attr doesn't exist
    # sync_platform_orders creates its own client internally using integration_service, so we are fine.
    pass

    # Chunk by day for precise audit
    # Chunk by day
    intervals = []
    current = start_date
    while current < end_date:
        day_end = current + timedelta(days=1)
        if day_end > end_date:
            day_end = end_date
        intervals.append((current, day_end))
        current = day_end
        
    logger.info(f"   >> Parallel Audit for {len(intervals)} days...")

    # Limit concurrency to avoid rate limits (365 days is a lot)
    sem = asyncio.Semaphore(10)

    async def audit_day(interval):
        async with sem:
            s, e = interval
            # DB access is blocking (sync session), but fast enough to block briefly
            # API access is async, allowing concurrency
            try:
                api_val = await get_platform_total(client, config, s, e)
                db_val = get_db_count(db, config.platform, s, e)
                return (s, e, api_val, db_val)
            except Exception as e:
                logger.error(f"Audit failed for {s.date()}: {e}")
                return (s, e, -1, -1)
        
    # Run audits in parallel
    results = await asyncio.gather(*[audit_day(i) for i in intervals])
    
    total_missing = 0
    total_fixed = 0
    
    mismatches = []
    
    # Process results
    for s, e, api_count, db_count in results:
        diff = api_count - db_count
        status = "✅ OK"
        if diff != 0:
            status = f"❌ DIFF: {diff}"
            total_missing += abs(diff)
            mismatches.append((s, e))
        
        logger.info(f"[{s.date()}] API: {api_count} | DB: {db_count} | {status}")

    # Fix Phase
    if fix and mismatches:
        logger.info(f"   >> Fixing {len(mismatches)} mismatched days...")
        for i, (s, e) in enumerate(mismatches):
            logger.info(f"   >> [{i+1}/{len(mismatches)}] Syncing {s.date()}...")
            try:
                stats = await sync_svc.sync_platform_orders(
                    config, 
                    time_from=s,
                    time_to=e
                )
                logger.info(f"      Sync Result: {stats}")
                total_fixed += stats.get("created", 0) + stats.get("updated", 0)
            except Exception as e:
                logger.error(f"      Failed to sync {s.date()}: {e}")
        
    logger.info(f"--- Completed {config.platform} ---")
    logger.info(f"Total Missing Detected: {total_missing}")
    if fix:
        logger.info(f"Total Fixed: {total_fixed}")

async def main():
    parser = argparse.ArgumentParser(description='Smart Sync Orders')
    parser.add_argument('--days', type=int, default=30, help='Days to look back')
    parser.add_argument('--fix', action='store_true', help='Perform sync if mismatch found')
    parser.add_argument('--platform', type=str, help='Specific platform (tiktok/shopee/lazada)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        configs = integration_service.get_platform_configs(db, is_active=True)
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=args.days)
        
        logger.info(f"Audit Range: {start_date} to {end_date}")
        
        for config in configs:
            if args.platform and config.platform != args.platform:
                continue
                
            await smart_sync_platform(db, config, start_date, end_date, fix=args.fix)
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
