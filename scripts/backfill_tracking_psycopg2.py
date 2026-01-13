
import psycopg2
import sys
import time
from psycopg2.extras import Json

print("Psycopg2 Script Starting...", flush=True)

DB_CONFIG = {
    "dbname": "weorder",
    "user": "chanack",
    "password": "chanack",
    "host": "localhost",
    "port": "5432"
}

BATCH_SIZE = 5000

def run():
    print("Connecting to DB...", flush=True)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Connected.", flush=True)

        total_processed = 0
        while True:
            # Query Logic
            query = f"""
                SELECT id 
                FROM order_header 
                WHERE channel_code = 'tiktok'
                AND raw_payload IS NOT NULL
                AND raw_payload->>'tracking_number' IS NOT NULL
                AND raw_payload->>'tracking_number' != ''
                AND tracking_number IS NULL
                ORDER BY id
                LIMIT {BATCH_SIZE}
            """
            print(f"Fetching batch (OFFSET {total_processed})...", flush=True)
            cur.execute(query)
            batch_ids = [row[0] for row in cur.fetchall()]
            
            if not batch_ids:
                print("No more records found. Finished.", flush=True)
                break
            
            print(f"Found {len(batch_ids)} records. Updating...", flush=True)
            
            # Format IDs for SQL IN clause
            batch_ids_str = ",".join([f"'{uid}'" for uid in batch_ids])
            
            update_sql = f"""
                UPDATE order_header
                SET tracking_number = raw_payload->>'tracking_number'
                WHERE id IN ({batch_ids_str})
            """
            cur.execute(update_sql)
            conn.commit()
            
            total_processed += len(batch_ids)
            print(f"Committed batch. Total: {total_processed}", flush=True)
            
    except Exception as e:
        print(f"Error: {e}", flush=True)
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("DB closed.", flush=True)

if __name__ == "__main__":
    run()
