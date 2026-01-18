#!/usr/bin/env python3
"""
Auto Sync Scheduler - Runs every hour to sync orders and finance data
Usage: python scheduler.py

Features:
- Log rotation (keep 7 days, max 50MB per file)
- Reduced SQL noise
- Summary logging only
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import os

# ====================
# LOGGING CONFIGURATION
# ====================

LOG_DIR = "/tmp/weorder_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Create rotating file handler (50MB max, keep 7 files = 350MB max)
file_handler = RotatingFileHandler(
    f"{LOG_DIR}/scheduler.log",
    maxBytes=50*1024*1024,  # 50MB
    backupCount=7,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Console handler (show in terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))

# IMPORTANT: Disable noisy loggers BEFORE basicConfig
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Setup root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)


# ====================
# SYNC FUNCTIONS
# ====================

async def sync_orders():
    """Sync orders from all platforms (last 3 days)"""
    from app.core.database import SessionLocal
    from app.models.integration import PlatformConfig
    from app.services.sync_service import OrderSyncService
    
    db = SessionLocal()
    try:
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform.in_(['shopee', 'tiktok', 'lazada'])
        ).all()
        
        service = OrderSyncService(db)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        total_fetched = 0
        total_created = 0
        total_updated = 0
        
        for config in configs:
            try:
                result = await service.sync_platform_orders(config, start_date, end_date)
                fetched = result.get('fetched', 0)
                created = result.get('created', 0)
                updated = result.get('updated', 0) if isinstance(result.get('updated'), int) else 0
                
                total_fetched += fetched
                total_created += created
                total_updated += updated
                
                logger.info(f"  ✓ {config.platform}: fetched={fetched}, new={created}")
            except Exception as e:
                logger.error(f"  ✗ {config.platform}: {str(e)[:100]}")
        
        return {'fetched': total_fetched, 'created': total_created, 'updated': total_updated}
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
        
        total_txs = 0
        
        for config in configs:
            try:
                result = await service.sync_platform_finance(config, start_date, end_date)
                txs = result.get('transactions', 0) if isinstance(result, dict) else 0
                total_txs += txs
                logger.info(f"  ✓ {config.platform} finance: {txs} transactions")
            except Exception as e:
                logger.error(f"  ✗ {config.platform} finance: {str(e)[:100]}")
        
        return {'transactions': total_txs}
    finally:
        db.close()


def run_sync():
    """Run all sync tasks"""
    start_time = datetime.now()
    logger.info("=" * 50)
    logger.info(f"🔄 Starting sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Sync orders
        logger.info("📦 Syncing orders (last 3 days)...")
        order_result = asyncio.run(sync_orders())
        
        # Sync finance
        logger.info("💰 Syncing finance (last 7 days)...")
        finance_result = asyncio.run(sync_finance())
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Sync completed in {duration:.1f}s")
        logger.info(f"   Orders: fetched={order_result.get('fetched', 0)}, new={order_result.get('created', 0)}")
        logger.info(f"   Finance: {finance_result.get('transactions', 0)} transactions")
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
    
    logger.info("=" * 50)


def main():
    logger.info("🚀 WeOrder Scheduler Started")
    logger.info(f"   Log dir: {LOG_DIR}")
    logger.info(f"   Schedule: Every hour at :00")
    logger.info(f"   Finance: Also at 08:00 and 20:00")
    
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
