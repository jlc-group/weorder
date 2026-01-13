
import sys
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

print("Script v2 starting...", flush=True)

DB_URL = "postgresql://postgres:postgres@localhost:5432/weorder"
BATCH_SIZE = 5000

def run():
    print("Creating DB engine...", flush=True)
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    print("DB Session created.", flush=True)

    try:
        total_processed = 0
        while True:
            print(f"Fetching batch (OFFSET {total_processed})...", flush=True)
            # Use simple loop logic: Fetch IDs where tracking_number IS NULL
            # logic: channel_code='tiktok', raw has tracking, tracking is null
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
                print("No more records found. Exiting.", flush=True)
                break
            
            print(f"Found {len(batch_ids)} records. Updating...", flush=True)
            batch_ids_str = ",".join([f"'{uid}'" for uid in batch_ids])
            
            update_sql = text(f"""
                UPDATE order_header
                SET tracking_number = raw_payload->>'tracking_number'
                WHERE id IN ({batch_ids_str})
            """)
            db.execute(update_sql)
            db.commit()
            total_processed += len(batch_ids)
            print(f"Committed batch. Total: {total_processed}", flush=True)
            
    except Exception as e:
        print(f"Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
        print("DB Session closed.", flush=True)

if __name__ == "__main__":
    run()
