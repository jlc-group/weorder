
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.services.order_service import OrderService
from app.services import integration_service
from app.models import OrderHeader
from app.integrations.tiktok import TikTokClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATUS_TO_CHECK = ['PAID', 'PACKING', 'READY_TO_SHIP', 'SHIPPED']

async def update_tiktok_orders(db):
    """Update status for active TikTok orders"""
    logger.info("Checking TikTok orders...")
    
    # 1. Get TikTok config
    configs = integration_service.get_platform_configs(db, platform='tiktok', is_active=True)
    if not configs:
        logger.warning("No active TikTok config found.")
        return

    client = integration_service.get_client_for_config(configs[0])
    
    # 2. Find active orders in DB
    orders = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'tiktok',
        OrderHeader.status_normalized.in_(STATUS_TO_CHECK)
    ).all()
    
    logger.info(f"Found {len(orders)} active TikTok orders to check.")
    
    updated_count = 0
    
    # 3. Check each order in batches
    chunk_size = 50
    total_orders = len(orders)
    logger.info(f"Processing {total_orders} orders in batches of {chunk_size}...")
    
    for i in range(0, total_orders, chunk_size):
        chunk = orders[i:i + chunk_size]
        ext_ids = [o.external_order_id for o in chunk]
        order_map = {o.external_order_id: o for o in chunk}
        
        try:
            details = await client.get_order_details_batch(ext_ids)
            logger.info(f"Batch {i//chunk_size + 1}: Requested {len(chunk)}, Got {len(details)}")
            
            for detail in details:
                ext_id = str(detail.get("order_id") or detail.get("id"))
                order = order_map.get(ext_id)
                
                if not order:
                    continue
                    
                current_raw_status = detail.get("status")
                new_normalized_status = client.normalize_order_status(current_raw_status)
                
                # Check if changed
                if new_normalized_status != order.status_normalized:
                    logger.info(f"Order {order.external_order_id}: {order.status_normalized} -> {new_normalized_status} ({current_raw_status})")
                    
                    # Extract actual status change date from TikTok API
                    update_time = detail.get("update_time")
                    status_changed_at = datetime.fromtimestamp(update_time) if update_time else None
                    
                    # Update DB via OrderService (triggers ledger logic with correct date)
                    success, msg = OrderService.update_status(
                        db, 
                        order.id, 
                        new_normalized_status,
                        performed_by=None, # System update
                        status_changed_at=status_changed_at  # Pass actual date
                    )
                    
                    if success:
                        # Also update raw status just in case
                        order.status_raw = current_raw_status
                        db.commit()
                        updated_count += 1
                    else:
                        logger.error(f"Failed to update {order.external_order_id}: {msg}")
                        
        except Exception as e:
            logger.error(f"Error processing batch {i}: {e}")
            continue
            
    logger.info(f"TikTok Status Update Complete. Updated: {updated_count}")

async def main():
    db = SessionLocal()
    try:
        await update_tiktok_orders(db)
        # Add Shopee here later
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
