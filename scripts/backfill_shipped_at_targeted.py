
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core import SessionLocal
from app.models.order import OrderHeader
from app.services import integration_service
from app.integrations.shopee import ShopeeClient
from app.integrations.tiktok import TikTokClient

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def backfill_shopee(db, config):
    logger.info(f"--- Backfilling Shopee ({config.shop_name}) ---")
    client = ShopeeClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    # 1. Provide a way to refresh token if needed
    try:
        await client.ensure_valid_token()
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        return

    # 2. Query target orders
    query = text("""
        SELECT external_order_id 
        FROM order_header 
        WHERE channel_code = 'shopee' 
          AND status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
          AND shipped_at IS NULL
          AND order_datetime >= '2025-01-01'
        ORDER BY order_datetime DESC
    """)
    result = db.execute(query).fetchall()
    order_ids = [row[0] for row in result]
    
    logger.info(f"Found {len(order_ids)} Shopee orders missing shipped_at")
    
    # 3. Process in batches
    chunk_size = 50
    total_updated = 0
    
    for i in range(0, len(order_ids), chunk_size):
        batch_ids = order_ids[i:i+chunk_size]
        logger.info(f"Processing batch {i}-{i+len(batch_ids)} / {len(order_ids)}")
        
        try:
            # Batch API Call
            details = await client.get_order_details_batch(batch_ids)
            
            updates = 0
            for raw_order in details:
                # Extract pickup time
                pickup_time = raw_order.get("pickup_done_time")
                if pickup_time:
                    shipped_at = datetime.fromtimestamp(pickup_time)
                    order_sn = raw_order.get("order_sn")
                    
                    # Update DB
                    db.execute(
                        text("UPDATE order_header SET shipped_at = :shipped_at WHERE external_order_id = :order_id AND channel_code = 'shopee'"),
                        {"shipped_at": shipped_at, "order_id": order_sn}
                    )
                    updates += 1
            
            db.commit()
            total_updated += updates
            logger.info(f"  -> Updated {updates} orders in this batch")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            
    logger.info(f"Shopee Backfill Complete. Total Updated: {total_updated}")

async def backfill_tiktok(db, config):
    logger.info(f"--- Backfilling TikTok ({config.shop_name}) ---")
    client = TikTokClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    try:
        await client.ensure_valid_token()
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        return

    query = text("""
        SELECT external_order_id 
        FROM order_header 
        WHERE channel_code = 'tiktok' 
          AND status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
          AND shipped_at IS NULL
          AND order_datetime >= '2025-01-01'
        ORDER BY order_datetime DESC
    """)
    result = db.execute(query).fetchall()
    order_ids = [row[0] for row in result]
    
    logger.info(f"Found {len(order_ids)} TikTok orders missing shipped_at")
    
    chunk_size = 50
    total_updated = 0
    
    for i in range(0, len(order_ids), chunk_size):
        batch_ids = order_ids[i:i+chunk_size]
        logger.info(f"Processing batch {i}-{i+len(batch_ids)} / {len(order_ids)}")
        
        try:
            details = await client.get_order_details_batch(batch_ids)
            
            updates = 0
            for raw_order in details:
                # Extract collection time (TikTok raw payload might differ slightly in batch response vs search)
                # Check different fields just in case
                collection_time = raw_order.get("collection_time") or raw_order.get("rts_time")
                
                if collection_time:
                    # TikTok V2 uses seconds usually, but check digit count
                    if collection_time > 9999999999:
                        collection_time = collection_time / 1000
                        
                    shipped_at = datetime.fromtimestamp(collection_time)
                    order_id = raw_order.get("order_id") or raw_order.get("id")
                    
                    db.execute(
                        text("UPDATE order_header SET shipped_at = :shipped_at WHERE external_order_id = :order_id AND channel_code = 'tiktok'"),
                        {"shipped_at": shipped_at, "order_id": order_id}
                    )
                    updates += 1
            
            db.commit()
            total_updated += updates
            logger.info(f"  -> Updated {updates} orders in this batch")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            
    logger.info(f"TikTok Backfill Complete. Total Updated: {total_updated}")

async def main():
    print("Starting Main...")
    db = SessionLocal()
    try:
        print("Getting configs...")
        configs = integration_service.get_platform_configs(db, is_active=True)
        print(f"Got {len(configs)} configs")
        
        for config in configs:
            print(f"Checking config: {config.platform}")
            if config.platform == 'shopee':
                await backfill_shopee(db, config)
            elif config.platform == 'tiktok':
                await backfill_tiktok(db, config)
                
    except Exception as e:
        print(f"Main Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
