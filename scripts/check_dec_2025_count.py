import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings

def check_order_counts():
    print(f"Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Count Dec 2025
        query_dec = text("""
            SELECT count(*), count(CASE WHEN channel_code = 'shopee' THEN 1 END) 
            FROM order_header 
            WHERE order_datetime >= '2025-12-01' AND order_datetime < '2026-01-01'
        """)
        result_dec = conn.execute(query_dec).fetchone()
        
        # Count Jan 2026
        query_jan = text("""
            SELECT count(*), count(CASE WHEN channel_code = 'shopee' THEN 1 END) 
            FROM order_header 
            WHERE order_datetime >= '2026-01-01'
        """)
        result_jan = conn.execute(query_jan).fetchone()
        
        print("\n=== Order Counts ===")
        print(f"Dec 2025 Total: {result_dec[0]}")
        print(f"Dec 2025 Shopee: {result_dec[1]}")
        print(f"Jan 2026 Total: {result_jan[0]}")
        print(f"Jan 2026 Shopee: {result_jan[1]}")
        print("==================\n")

if __name__ == "__main__":
    check_order_counts()
