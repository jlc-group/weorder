"""
Backfill Stock Ledger Dates

One-time script to fix historical stock_ledger entries that have incorrect dates.
Updates created_at to match the order's order_datetime (best approximation of ship date).

Run: python scripts/sync/backfill_stock_dates.py
"""
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core import SessionLocal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backfill_stock_dates():
    """Update stock_ledger created_at to match related order's order_datetime"""
    db = SessionLocal()
    
    try:
        # Count affected records
        count_query = text("""
            SELECT COUNT(*) 
            FROM stock_ledger sl
            JOIN order_header oh ON sl.reference_id = oh.id::text
            WHERE sl.reference_type = 'ORDER' 
            AND sl.movement_type = 'OUT'
            AND DATE(sl.created_at) != DATE(oh.order_datetime)
        """)
        
        result = db.execute(count_query)
        count = result.scalar()
        
        logger.info(f"Found {count} stock_ledger entries with mismatched dates")
        
        if count == 0:
            logger.info("Nothing to update!")
            return
        
        # Update query: set stock_ledger.created_at = order_header.order_datetime
        update_query = text("""
            UPDATE stock_ledger
            SET created_at = oh.order_datetime
            FROM order_header oh
            WHERE stock_ledger.reference_id = oh.id::text
            AND stock_ledger.reference_type = 'ORDER'
            AND stock_ledger.movement_type = 'OUT'
            AND DATE(stock_ledger.created_at) != DATE(oh.order_datetime)
        """)
        
        result = db.execute(update_query)
        db.commit()
        
        logger.info(f"Updated {result.rowcount} stock_ledger entries with correct dates")
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting Stock Ledger Date Backfill...")
    backfill_stock_dates()
    logger.info("Backfill complete!")
