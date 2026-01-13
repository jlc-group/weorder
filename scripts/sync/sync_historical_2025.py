
import asyncio
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.core import get_db
from app.services import integration_service, sync_service
from app.models.integration import PlatformConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
# Aggressively silence noisy loggers
for logger_name in ["sqlalchemy.engine", "sqlalchemy.pool", "sqlalchemy.dialects", "sqlalchemy.orm", "httpx", "httpcore", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# FORCE DISABLE SQLALCHEMY ECHO (The Real Fix)
from app.core.database import engine
engine.echo = False

async def sync_platform_history(config: PlatformConfig, start_date: datetime, end_date: datetime):
    """
    Sync history for a platform from start_date to end_date
    Chunking by 15 days to avoid timeout/large payload issues
    """
    current_start = start_date
    db = next(get_db())
    
    service = sync_service.OrderSyncService(db)
    
    total_stats = {"fetched": 0, "created": 0, "updated": 0, "errors": 0}

    logger.info(f"--- Starting Sync for {config.platform} ({config.shop_name}) ---")
    logger.info(f"--- Period: {start_date.date()} to {end_date.date()} ---")
    
    while current_start < end_date:
        # 15-day chunks to be safe with API limits
        current_end = current_start + timedelta(days=15)
        if current_end > end_date:
            current_end = end_date
            
        logger.info(f"Syncing range: {current_start.date()} to {current_end.date()}")
        
        try:
            stats = await service.sync_platform_orders(
                config,
                time_from=current_start,
                time_to=current_end
            )
            
            total_stats["fetched"] += stats.get("fetched", 0)
            total_stats["created"] += stats.get("created", 0)
            total_stats["updated"] += stats.get("updated", 0)
            total_stats["errors"] += stats.get("errors", 0)
            
            logger.info(f"Process stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error syncing {current_start.date()} - {current_end.date()}: {e}")
        
        # Move to next chunk
        current_start = current_end + timedelta(seconds=1)
        
        # Rate limit protection
        await asyncio.sleep(1)

    logger.info(f"--- Completed {config.platform} ---")
    logger.info(f"Total: {total_stats}")
    return total_stats

async def main():
    db = next(get_db())
    try:
        # Get all actively synced platforms
        configs = integration_service.get_platform_configs(db, is_active=True)
        active_configs = [c for c in configs if c.sync_enabled]
        
        logger.info(f"Found {len(active_configs)} active platforms to sync.")
        
        # Sync from Jan 1, 2025 to NOW
        start_date = datetime(2025, 1, 1)
        end_date = datetime.now()
        
        logger.info(f"=== HISTORICAL SYNC: {start_date.date()} to {end_date.date()} ===")
        
        all_results = {}
        for config in active_configs:
            result = await sync_platform_history(config, start_date, end_date)
            all_results[config.platform] = result
        
        # Summary
        logger.info("=" * 50)
        logger.info("=== FINAL SUMMARY ===")
        for platform, stats in all_results.items():
            logger.info(f"{platform}: fetched={stats['fetched']}, created={stats['created']}, updated={stats['updated']}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

