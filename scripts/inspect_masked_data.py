import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from app.core import settings

def inspect_raw_data():
    # Create a fresh sync engine to avoid async issues
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Fetch the raw platform_invoice_data for the 4 records
        query = text("""
            SELECT order_id, invoice_name, tax_id, platform_invoice_data
            FROM invoice_profile
            LIMIT 5
        """)
        result = conn.execute(query)
        rows = result.fetchall()

        print(f"Found {len(rows)} records.")
        for row in rows:
            print("-" * 50)
            print(f"Order ID: {row[0]}")
            print(f"Saved Name: {row[1]}")
            print(f"Saved Tax ID: {row[2]}")
            print("RAW JSON DATA:")
            # Pretty print JSON
            try:
                print(json.dumps(row[3], indent=2, ensure_ascii=False))
            except:
                print(row[3])
            print("-" * 50)

if __name__ == "__main__":
    inspect_raw_data()
