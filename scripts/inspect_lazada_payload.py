import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from app.core import settings

def inspect_raw_order_payload():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Fetch the raw_payload from OrderHeader for the problematic orders
        # Using the same order_ids from previous check
        query = text("""
            SELECT o.external_order_id, o.raw_payload
            FROM order_header o
            WHERE o.external_order_id = '1074255913052684' AND o.channel_code = 'lazada'
            LIMIT 1
        """)
        result = conn.execute(query)
        rows = result.fetchall()

        print(f"Found {len(rows)} records.")
        for row in rows:
            print("-" * 50)
            print(f"Lazada Order ID: {row[0]}")
            print("RAW ORDER PAYLOAD (From Lazada API):")
            # Pretty print JSON
            try:
                print(json.dumps(row[1], indent=2, ensure_ascii=False))
            except:
                print(row[1])
            print("-" * 50)

if __name__ == "__main__":
    inspect_raw_order_payload()
