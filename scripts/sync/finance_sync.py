
import sys
import os
import asyncio
import logging
import argparse
from datetime import datetime, timedelta, timezone

sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.services.finance_sync_service import FinanceSyncService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_finance_sync():
    parser = argparse.ArgumentParser(description='Sync Finance Data (Money Trail)')
    parser.add_argument('--days', type=int, default=30, help='Days to look back')
    parser.add_argument('--platform', type=str, help='Specific platform (tiktok, shopee, lazada)')
    parser.add_argument('--full-year', action='store_true', help='Sync entire current year (Jan 1 to Now)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = FinanceSyncService(db)
        
        # Determine Date Range
        end_date = datetime.now(timezone.utc)
        
        if args.start_date:
            try:
                # Parse naive date and set to UTC
                dt = datetime.strptime(args.start_date, "%Y-%m-%d")
                start_date = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error("Invalid date format. Use YYYY-MM-DD")
                return
        elif args.full_year:
            start_date = datetime(end_date.year, 1, 1, tzinfo=timezone.utc)
        else:
            start_date = end_date - timedelta(days=args.days)

        logger.info(f"💰 Starting Finance Sync: {start_date.date()} -> {end_date.date()}")

        # Get Configs
        query = db.query(PlatformConfig).filter(PlatformConfig.is_active == True)
        if args.platform:
            query = query.filter(PlatformConfig.platform == args.platform)
        
        configs = query.all()
        
        if not configs:
            logger.warning("No active platform configs found.")
            return

        for config in configs:
            logger.info(f"--- Syncing {config.platform} ({config.shop_name}) ---")
            try:
                # Sync in chunks to avoid timeouts if range is large
                current = start_date
                chunk_days = 7 # Weekly chunks
                
                total_stats = {"fetched": 0, "created": 0, "errors": 0}
                
                while current < end_date:
                    chunk_end = min(current + timedelta(days=chunk_days), end_date)
                    logger.info(f"   Batch: {current.date()} -> {chunk_end.date()}")
                    
                    stats = await service.sync_platform_finance(
                        config, 
                        time_from=current,
                        time_to=chunk_end
                    )
                    
                    total_stats["fetched"] += stats.get("fetched", 0)
                    total_stats["created"] += stats.get("created", 0)
                    total_stats["errors"] += stats.get("errors", 0)
                    
                    current = chunk_end
                    
                logger.info(f"✅ Completed {config.platform}: {total_stats}")

            except Exception as e:
                logger.error(f"❌ Failed to sync {config.platform}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_finance_sync())
