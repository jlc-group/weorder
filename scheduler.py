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


async def refresh_tokens():
    """Refresh tokens for all platforms before they expire"""
    from app.core.database import SessionLocal
    from app.models.integration import PlatformConfig
    from app.services import integration_service
    
    db = SessionLocal()
    results = {}
    
    try:
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.sync_enabled == True
        ).all()
        
        for config in configs:
            try:
                # Check if token expires in less than 2 hours
                if config.token_expires_at:
                    time_until_expiry = (config.token_expires_at - datetime.now()).total_seconds()
                    if time_until_expiry > 7200:  # More than 2 hours left
                        logger.info(f"  ⏭ {config.platform}: Token OK ({time_until_expiry/3600:.1f}h remaining)")
                        continue
                
                # Refresh token
                client = integration_service.get_client_for_config(config)
                result = await client.refresh_access_token()
                
                # Update tokens in DB
                config.access_token = result['access_token']
                if result.get('refresh_token'):
                    config.refresh_token = result['refresh_token']
                expires_in = result.get('expires_in', 3600)
                config.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                db.commit()
                
                results[config.platform] = {'status': 'OK', 'expires_in': expires_in}
                logger.info(f"  ✓ {config.platform}: Token refreshed ({expires_in/3600:.1f}h)")
            except Exception as e:
                results[config.platform] = {'status': 'ERROR', 'error': str(e)}
                logger.error(f"  ✗ {config.platform}: {str(e)[:100]}")
        
        return results
    finally:
        db.close()


def run_token_refresh():
    """Run token refresh"""
    logger.info("🔑 Refreshing tokens...")
    try:
        result = asyncio.run(refresh_tokens())
        logger.info(f"✅ Token refresh completed: {len(result)} platforms")
    except Exception as e:
        logger.error(f"❌ Token refresh failed: {e}")


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
    logger.info(f"   Schedule: Twice daily at 08:00 and 20:00")
    logger.info(f"   Token Refresh: Every 3 hours")
    logger.info(f"   Note: Webhooks handle real-time updates, Sync is backup only")
    
    # Refresh tokens immediately on start
    run_token_refresh()
    
    # DO NOT run sync on start - let webhooks handle real-time
    # Sync is backup only, runs twice daily
    
    # Token refresh every 3 hours (before Shopee token expires at 4h)
    schedule.every(3).hours.do(run_token_refresh)
    
    # Sync twice daily only (backup for missed webhooks)
    schedule.every().day.at("08:00").do(run_sync)
    schedule.every().day.at("20:00").do(run_sync)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
