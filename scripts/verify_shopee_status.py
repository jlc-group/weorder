import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import desc
from app.core import SessionLocal
from app.models.order import OrderHeader
from app.services.integration_service import get_client_for_config, get_platform_configs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def verify_status():
    db = SessionLocal()
    try:
        # Get Shopee config
        configs = get_platform_configs(db, "shopee")
        if not configs:
            logger.error("No Shopee configuration found")
            return

        config = configs[0] # Assuming single shop for now
        client = get_client_for_config(config)
        
        # Get orders that are "READY_TO_SHIP" in DB
        # Sort by creation date desc to check most recent first
        orders = db.query(OrderHeader).filter(
            OrderHeader.status_raw == "READY_TO_SHIP",
            OrderHeader.channel_code == "shopee"
        ).order_by(desc(OrderHeader.order_datetime)).limit(50).all()
        
        logger.info(f"Checking {len(orders)} orders with DB status 'READY_TO_SHIP'...")
        
        mismatches = 0
        
        for order in orders:
            try:
                # Fetch live status from Shopee
                detail = await client.get_order_detail(order.external_order_id)
                if not detail:
                    logger.warning(f"Could not fetch details for {order.external_order_id}")
                    continue
                    
                api_status = detail.get("order_status")
                
                if api_status != "READY_TO_SHIP":
                    logger.error(f"❌ MISMATCH: {order.external_order_id}")
                    logger.error(f"   - DB Status : READY_TO_SHIP")
                    logger.error(f"   - API Status: {api_status}")
                    logger.error(f"   -> Suggests order has moved on but DB not updated.")
                    mismatches += 1
                else:
                    logger.info(f"✅ MATCH: {order.external_order_id} is still READY_TO_SHIP")
                    
                # Rate limit
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error checking {order.external_order_id}: {e}")
                
        logger.info("-" * 50)
        logger.info(f"Verification Complete.")
        logger.info(f"Total Checked: {len(orders)}")
        logger.info(f"Total Mismatches: {mismatches}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_status())
