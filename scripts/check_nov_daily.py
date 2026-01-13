import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings

def check_nov_daily():
    print(f"Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        query = text("""
            SELECT TO_CHAR(order_datetime, 'YYYY-MM-DD') as day, count(*)
            FROM order_header 
            WHERE channel_code = 'shopee' 
            AND order_datetime >= '2025-11-01' 
            AND order_datetime < '2025-12-01'
            GROUP BY day
            ORDER BY day ASC
        """)
        result = conn.execute(query).fetchall()
        
        print("\n=== Shopee Orders: Nov 2025 (Daily) ===")
        print(f"{'Date':<12} | {'Count'}")
        print("-" * 20)
        
        total = 0
        for row in result:
            print(f"{row[0]:<12} | {row[1]}")
            total += row[1]
            
        print("-" * 20)
        print(f"{'TOTAL':<12} | {total}")

if __name__ == "__main__":
    check_nov_daily()
