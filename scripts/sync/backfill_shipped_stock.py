"""
Backfill Stock Ledger for Historical Shipped Orders

This script creates stock_ledger OUT entries for all orders that are 
SHIPPED or DELIVERED but don't have corresponding stock movements.

Run: python scripts/sync/backfill_shipped_stock.py
"""
import sys
import os

sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core import SessionLocal
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backfill_shipped_stock():
    """Create stock_ledger entries for shipped orders that don't have them"""
    db = SessionLocal()
    
    try:
        # 0. Get default warehouse
        default_wh = db.execute(text("SELECT id FROM warehouse LIMIT 1")).fetchone()
        if not default_wh:
            logger.error("No warehouse found in database!")
            return
        
        default_wh_id = str(default_wh[0])
        logger.info(f"Using default warehouse: {default_wh_id}")
        
        # 1. Find orders that are SHIPPED/DELIVERED but have no stock_ledger entry
        logger.info("Finding shipped orders without stock_ledger entries...")
        
        count_query = text("""
            SELECT COUNT(DISTINCT oh.id)
            FROM order_header oh
            WHERE oh.status_normalized IN ('SHIPPED', 'DELIVERED')
            AND NOT EXISTS (
                SELECT 1 FROM stock_ledger sl 
                WHERE sl.reference_id = oh.id::text 
                AND sl.reference_type = 'ORDER'
                AND sl.movement_type = 'OUT'
            )
        """)
        
        count = db.execute(count_query).scalar()
        logger.info(f"Found {count:,} orders without stock_ledger entries")
        
        if count == 0:
            logger.info("Nothing to backfill!")
            return
        
        # 2. Insert stock_ledger entries from order_items
        # Use order_datetime as created_at (best approximation of ship date)
        # Use default warehouse if order doesn't have one
        logger.info("Creating stock_ledger entries...")
        
        insert_query = text(f"""
            INSERT INTO stock_ledger (
                id, warehouse_id, product_id, movement_type, quantity,
                reference_type, reference_id, note, created_at
            )
            SELECT 
                gen_random_uuid(),
                COALESCE(oh.warehouse_id, '{default_wh_id}'::uuid),
                oi.product_id,
                'OUT',
                oi.quantity,
                'ORDER',
                oh.id::text,
                'Backfill: Order ' || oh.external_order_id,
                COALESCE(oh.order_datetime, oh.created_at)
            FROM order_header oh
            JOIN order_item oi ON oi.order_id = oh.id
            WHERE oh.status_normalized IN ('SHIPPED', 'DELIVERED')
            AND oi.product_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM stock_ledger sl 
                WHERE sl.reference_id = oh.id::text 
                AND sl.reference_type = 'ORDER'
                AND sl.movement_type = 'OUT'
            )
        """)
        
        result = db.execute(insert_query)
        db.commit()
        
        logger.info(f"Created {result.rowcount:,} stock_ledger entries")
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting Stock Ledger Backfill for Shipped Orders...")
    backfill_shipped_stock()
    logger.info("Backfill complete!")
