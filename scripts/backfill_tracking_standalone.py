
import logging
import os
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Bypass app.core.config and hardcode/simplify connection for script usage
# This avoids the Pydantic Settings hang
DB_URL = "postgresql://postgres:postgres@localhost:5432/weorder"

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)],
#     force=True
# )
# logger = logging.getLogger(__name__)

BATCH_SIZE = 5000

def get_db_session():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def backfill_tracking_standalone():
    print("Starting standalone tracking backfill...", flush=True)
    db = get_db_session()
    try:
        total_processed = 0
        
        while True:
            # Fetch orders with tracking number in payload but NULL in column
            print(f"Fetching next {BATCH_SIZE} orders for tracking update...", flush=True)
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
                print("No more tracking numbers to update. Finished.", flush=True)
                break
                
            batch_ids_str = ",".join([f"'{uid}'" for uid in batch_ids])
            print(f"Updating batch of {len(batch_ids)} orders...", flush=True)
            
            update_sql = text(f"""
                UPDATE order_header
                SET tracking_number = raw_payload->>'tracking_number'
                WHERE id IN ({batch_ids_str});
            """)
            db.execute(update_sql)
            
            db.commit()
            total_processed += len(batch_ids)
            print(f"Committed batch. Total tracking numbers updated: {total_processed}", flush=True)
            
    except Exception as e:
        print(f"Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_tracking_standalone()
