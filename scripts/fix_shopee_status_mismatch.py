import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import desc
from app.core import SessionLocal
from app.models.order import OrderHeader
from app.services.integration_service import get_client_for_config, get_platform_configs
from app.services.order_service import OrderService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fix_status():
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
        ).order_by(desc(OrderHeader.order_datetime)).all()
        
        total_orders = len(orders)
        logger.info(f"Checking {total_orders} orders with DB status 'READY_TO_SHIP'...")
        
        fixed_count = 0
        error_count = 0
        
        for i, order in enumerate(orders):
            try:
                # Fetch live status from Shopee
                detail = await client.get_order_detail(order.external_order_id)
                if not detail:
                    logger.warning(f"[{i+1}/{total_orders}] Could not fetch details for {order.external_order_id}")
                    continue
                    
                api_status = detail.get("order_status")
                
                if api_status != "READY_TO_SHIP":
                    logger.info(f"[{i+1}/{total_orders}] 🔄 FIXING: {order.external_order_id}")
                    logger.info(f"   DB: READY_TO_SHIP -> API: {api_status}")
                    
                    # Normalize Status
                    normalized_status = client.normalize_order_status(api_status)
                    
                    # Update DB
                    order.status_raw = api_status
                    # Use service to update normalized status if needed, but direct is safer for fix script to avoid side effects?
                    # Better to use Service to ensure ledgers/consistency if we were doing full logic.
                    # But for quick fix, let's update directly BUT accurate.
                    
                    # Actually, we should use OrderService to update status so it tracks history?
                    # But OrderService.update_status requires "performed_by".
                    
                    # Let's update directly for this fix to be surgical.
                    order.status_normalized = normalized_status
                    
                    # Try to get update time
                    update_time = detail.get("update_time")
                    if update_time:
                         order.updated_at = datetime.fromtimestamp(update_time)
                    
                    db.commit()
                    fixed_count += 1
                else:
                    # logger.info(f"[{i+1}/{total_orders}] ✅ MATCH: {order.external_order_id} is correctly READY_TO_SHIP")
                    pass
                    
                # Rate limit
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error checking {order.external_order_id}: {e}")
                error_count += 1
                db.rollback()
                
        logger.info("-" * 50)
        logger.info(f"Fix Complete.")
        logger.info(f"Total Checked: {total_orders}")
        logger.info(f"Total Fixed: {fixed_count}")
        logger.info(f"Total Errors: {error_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_status())
