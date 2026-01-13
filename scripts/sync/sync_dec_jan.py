
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
from app.services import integration_service
from app.integrations.shopee import ShopeeClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.services.sync_service import OrderSyncService

async def sync_orders_range(start_date: datetime, end_date: datetime):
    db = next(get_db())
    try:
        # 1. Get Config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs:
            logger.error("No active Shopee config")
            return
        
        config = configs[0]
        sync_service = OrderSyncService(db)
        
        logger.info(f"Syncing Shopee: {config.shop_name}")
        logger.info(f"Range: {start_date} to {end_date}")

        # 2. Iterate by 7-day chunks to avoid timeouts/limits (Shopee limits usually)
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=7), end_date)
            logger.info(f"Processing chunk: {current_start.date()} -> {current_end.date()}")
            
            try:
                stats = await sync_service.sync_platform_orders(
                    config=config,
                    time_from=current_start,
                    time_to=current_end
                )
                logger.info(f"Stats: {stats}")
                
            except Exception as e:
                logger.error(f"Chunk failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            current_start = current_end
            # Tiny sleep to let other tasks breathe
            await asyncio.sleep(1)
            
    finally:
        db.close()

if __name__ == "__main__":
    # Range: Dec 1, 2025 to Now (Jan 4+, 2026)
    start = datetime(2025, 12, 1)
    end = datetime.now()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(sync_orders_range(start, end))
