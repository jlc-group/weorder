import sys
import os
from sqlalchemy import create_engine, text
import json

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings

def check_shopee_toship():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check counts by status for Shopee
        query = text("""
            SELECT status_normalized, status_raw, count(*)
            FROM order_header
            WHERE channel_code = 'shopee'
            GROUP BY status_normalized, status_raw
            ORDER BY status_normalized
        """)
        result = conn.execute(query).fetchall()
        
        print("\n=== WeOrder: Shopee Orders (Likely 'To Ship') ===")
        total_toship = 0
        for row in result:
            print(f"Normalized: {row[0]:<15} | Raw: {row[1]:<20} | Count: {row[2]}")
            total_toship += row[2]
            
        print("-" * 50)
        print(f"Total 'To Ship' in DB: {total_toship}")
        print("============================================\n")
        
        # Check raw payload of one 'PAID' order to see if we missed anything
        query_sample = text("""
            SELECT raw_payload 
            FROM order_header 
            WHERE channel_code = 'shopee' AND status_normalized = 'PAID' 
            LIMIT 1
        """)
        sample = conn.execute(query_sample).fetchone()
        if sample and sample[0]:
             print("Sample Raw Payload Status Data:")
             payload = sample[0]
             print(f"order_status: {payload.get('order_status')}")
             # Add other relevant fields if known

if __name__ == "__main__":
    check_shopee_toship()
