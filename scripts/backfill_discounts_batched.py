
import asyncio
import logging
import os
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
from app.core.config import settings
from app.core.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 10000

def backfill_batched():
    db = SessionLocal()
    try:
        # 1. Get IDs of orders to update
        logger.info("Fetching IDs of orders to update...")
        fetch_sql = text("""
            SELECT id 
            FROM order_header 
            WHERE channel_code = 'tiktok'
            AND raw_payload IS NOT NULL
            AND (
                COALESCE((raw_payload->'payment'->>'platform_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'seller_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'shipping_fee_platform_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'shipping_fee_seller_discount')::numeric, 0) > 0
            )
            AND discount_amount = 0  -- Only update un-processed ones
        """)
        
        result = db.execute(fetch_sql)
        order_ids = [row[0] for row in result.fetchall()]
        total_count = len(order_ids)
        logger.info(f"Found {total_count} orders to update.")

        if total_count == 0:
            logger.info("No orders to update. Exiting.")
            return

        # 2. Process in batches
        total_processed = 0
        
        for i in range(0, total_count, BATCH_SIZE):
            batch_ids = order_ids[i : i + BATCH_SIZE]
            batch_ids_str = ",".join([f"'{uid}'" for uid in batch_ids])
            
            logger.info(f"Processing batch {i} - {i+BATCH_SIZE} / {total_count}...")
            
            # Update Headers
            update_header_sql = text(f"""
                UPDATE order_header
                SET 
                    platform_discount_amount = COALESCE((raw_payload->'payment'->>'platform_discount')::numeric, 0) + 
                                             COALESCE((raw_payload->'payment'->>'shipping_fee_platform_discount')::numeric, 0),
                    discount_amount = COALESCE((raw_payload->'payment'->>'seller_discount')::numeric, 0) + 
                                    COALESCE((raw_payload->'payment'->>'shipping_fee_seller_discount')::numeric, 0),
                    order_discount_type = CASE WHEN (raw_payload->'payment'->>'seller_discount')::numeric > 0 THEN 'SELLER' 
                                               WHEN (raw_payload->'payment'->>'platform_discount')::numeric > 0 THEN 'PLATFORM'
                                               ELSE NULL END
                WHERE id IN ({batch_ids_str});
            """)
            db.execute(update_header_sql)
            
            # Update Items - optimized to only look at this batch
            update_item_sql = text(f"""
                WITH item_discounts AS (
                    SELECT 
                        oh.id as order_id,
                        elem->>'seller_sku' as info_sku,
                        COALESCE((elem->>'seller_discount')::numeric, 0) as item_seller_discount,
                        COALESCE((elem->>'platform_discount')::numeric, 0) as item_platform_discount
                    FROM order_header oh,
                         jsonb_array_elements(oh.raw_payload->'line_items') elem
                    WHERE oh.id IN ({batch_ids_str})
                )
                UPDATE order_item oi
                SET 
                    line_discount = id.item_seller_discount + id.item_platform_discount,
                    discount_source = CASE WHEN id.item_seller_discount > 0 THEN 'SELLER' ELSE 'PLATFORM' END
                FROM item_discounts id
                WHERE oi.order_id = id.order_id
                AND oi.sku = id.info_sku
                AND (id.item_seller_discount > 0 OR id.item_platform_discount > 0);
            """)
            db.execute(update_item_sql)
            
            db.commit()
            total_processed += len(batch_ids)
            logger.info(f"Committed batch. Total processed: {total_processed}")

    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_batched()
