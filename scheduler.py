#!/usr/bin/env python3
"""
Auto Sync Scheduler - Runs every hour to sync orders and finance data
Usage: python scheduler.py
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/weorder_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def sync_orders():
    """Sync orders from all platforms (last 3 days)"""
    from app.core.database import SessionLocal
    from app.models.integration import PlatformConfig
    from app.services.sync_service import OrderSyncService
    from datetime import timedelta
    
    db = SessionLocal()
    try:
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform.in_(['shopee', 'tiktok', 'lazada'])
        ).all()
        
        service = OrderSyncService(db)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        for config in configs:
            try:
                logger.info(f"Syncing {config.platform} orders...")
                result = await service.sync_platform_orders(config, start_date, end_date)
                logger.info(f"  {config.platform}: {result}")
            except Exception as e:
                logger.error(f"  {config.platform} error: {e}")
    finally:
        db.close()


async def sync_finance():
    """Sync finance data from all platforms (last 7 days)"""
    from app.core.database import SessionLocal
    from app.models.integration import PlatformConfig
    from app.services.finance_sync_service import FinanceSyncService
    
    db = SessionLocal()
    try:
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform.in_(['shopee', 'tiktok'])
        ).all()
        
        service = FinanceSyncService(db)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        for config in configs:
            try:
                logger.info(f"Syncing {config.platform} finance...")
                result = await service.sync_platform_finance(config, start_date, end_date)
                logger.info(f"  {config.platform}: {result}")
            except Exception as e:
                logger.error(f"  {config.platform} error: {e}")
    finally:
        db.close()


def run_sync():
    """Run all sync tasks"""
    logger.info("=" * 50)
    logger.info(f"Starting scheduled sync at {datetime.now()}")
    
    try:
        asyncio.run(sync_orders())
        asyncio.run(sync_finance())
        logger.info(f"Sync completed at {datetime.now()}")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    
    logger.info("=" * 50)


def main():
    logger.info("WeOrder Auto Sync Scheduler Started")
    logger.info("Schedule: Every hour at :00")
    
    # Run immediately on start
    run_sync()
    
    # Schedule to run every hour
    schedule.every().hour.at(":00").do(run_sync)
    
    # Also run at specific times for finance (twice daily)
    schedule.every().day.at("08:00").do(run_sync)
    schedule.every().day.at("20:00").do(run_sync)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
