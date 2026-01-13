
import asyncio
import json
import logging
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure we can import app modules
sys.path.append(os.getcwd())

from app.core.config import settings
from app.core.database import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def backfill_discounts():
    """
    Backfill discount information from raw_payload to order_header and order_item
    """
    db = SessionLocal()
    try:
        # 1. Update Order Header Discounts (TikTok)
        logger.info("Backfilling Order Header discounts for TikTok...")
        
        # Use a raw SQL query for efficiency with JSON extraction
        update_header_sql = text("""
            UPDATE order_header
            SET 
                platform_discount_amount = COALESCE((raw_payload->'payment'->>'platform_discount')::numeric, 0) + 
                                         COALESCE((raw_payload->'payment'->>'shipping_fee_platform_discount')::numeric, 0),
                discount_amount = COALESCE((raw_payload->'payment'->>'seller_discount')::numeric, 0) + 
                                COALESCE((raw_payload->'payment'->>'shipping_fee_seller_discount')::numeric, 0),
                order_discount_type = CASE WHEN (raw_payload->'payment'->>'seller_discount')::numeric > 0 THEN 'SELLER' 
                                           WHEN (raw_payload->'payment'->>'platform_discount')::numeric > 0 THEN 'PLATFORM'
                                           ELSE NULL END
            WHERE channel_code = 'tiktok'
            AND raw_payload IS NOT NULL
            AND (
                COALESCE((raw_payload->'payment'->>'platform_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'seller_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'shipping_fee_platform_discount')::numeric, 0) > 0 OR
                COALESCE((raw_payload->'payment'->>'shipping_fee_seller_discount')::numeric, 0) > 0
            );
        """)
        
        result = db.execute(update_header_sql)
        logger.info(f"Updated {result.rowcount} order headers with discount data.")
        db.commit()

        # 2. Update Order Item Discounts (TikTok)
        # This is more complex as we need to match items. 
        # Ideally we can use the order_id and some item identifier, but simplistic mapping might be safer for bulk updates if line_items are consistent.
        # But wait, raw_payload is in header. order_item has sku.
        # Let's try to update using a join if possible, or iterate if too complex for single SQL.
        # Given the volume (800k+), iterating in python is slow.
        # Check if we can do it via SQL using jsonb_array_elements.
        
        logger.info("Backfilling Order Item discounts for TikTok...")
        
        # Logic: 
        # Join order_item with order_header
        # Expand raw_payload->'line_items'
        # Match on sku or product_id? raw_payload has 'sku_id', 'product_id', 'seller_sku'.
        # order_item has 'sku'. Let's assume 'seller_sku' in json matches 'sku' in table.
        
        update_item_sql = text("""
            WITH item_discounts AS (
                SELECT 
                    oh.id as order_id,
                    elem->>'seller_sku' as info_sku,
                    COALESCE((elem->>'seller_discount')::numeric, 0) as item_seller_discount,
                    COALESCE((elem->>'platform_discount')::numeric, 0) as item_platform_discount
                FROM order_header oh,
                     jsonb_array_elements(oh.raw_payload->'line_items') elem
                WHERE oh.channel_code = 'tiktok'
                AND oh.raw_payload IS NOT NULL
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
        
        result_items = db.execute(update_item_sql)
        logger.info(f"Updated {result_items.rowcount} order items with discount data.")
        db.commit()
        
    except Exception as e:
        logger.error(f"Error backfilling discounts: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_discounts()
