import asyncio
import sys
import os
sys.path.append(os.getcwd())
import logging

from app.core import get_db
from app.services import integration_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_shopee():
    db = next(get_db())
    try:
        # Get Shopee Config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs:
            logger.error("No active Shopee config found!")
            return
            
        config = configs[0]
        logger.info(f"Checking Shopee Config: {config.shop_name} (ID: {config.shop_id})")
        
        # Get Client
        client = integration_service.get_client_for_config(config)
        logger.info("Client created successfully.")
        
        # Attempt to get orders (just 1 to test auth)
        logger.info("Attempting to fetch recent orders...")
        try:
            result = await client.get_orders(page_size=5)
            orders = result.get("orders", [])
            logger.info(f"Success! Found {len(orders)} orders.")
            if orders:
                logger.info(f"Sample Order ID: {orders[0].get('order_sn')}")
        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_shopee())
