
import asyncio
import logging
import os
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
print("DEBUG: Importing app config...", flush=True)
from app.core.config import settings
print("DEBUG: Importing app database...", flush=True)
from app.core.database import SessionLocal
print("DEBUG: Imports done.", flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000

def backfill_tracking():
    db = SessionLocal()
    try:
        total_processed = 0
        
        while True:
            # Fetch orders with tracking number in payload but NULL in column
            logger.info(f"Fetching next {BATCH_SIZE} orders for tracking update...")
            fetch_sql = text(f"""
                SELECT id 
                FROM order_header 
                WHERE channel_code = 'tiktok'
                AND raw_payload IS NOT NULL
                AND raw_payload->>'tracking_number' IS NOT NULL
                AND raw_payload->>'tracking_number' != ''
                AND tracking_number IS NULL
                ORDER BY id
                LIMIT {BATCH_SIZE}
            """)
            
            result = db.execute(fetch_sql)
            batch_ids = [row[0] for row in result.fetchall()]
            
            if not batch_ids:
                logger.info("No more tracking numbers to update. Finished.")
                break
                
            batch_ids_str = ",".join([f"'{uid}'" for uid in batch_ids])
            logger.info(f"Updating batch of {len(batch_ids)} orders...")
            
            update_sql = text(f"""
                UPDATE order_header
                SET tracking_number = raw_payload->>'tracking_number'
                WHERE id IN ({batch_ids_str});
            """)
            db.execute(update_sql)
            
            db.commit()
            total_processed += len(batch_ids)
            logger.info(f"Committed batch. Total tracking numbers updated: {total_processed}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_tracking()
