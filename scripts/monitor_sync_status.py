import time
import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())
from app.core import settings

def get_counts(conn):
    shopee_nov = conn.execute(text("SELECT count(*) FROM order_header WHERE channel_code='shopee' AND order_datetime >= '2025-11-01' AND order_datetime < '2025-12-01'")).scalar()
    
    tiktok_missing = conn.execute(text("SELECT count(*) FROM marketplace_transaction WHERE platform='tiktok' AND transaction_date >= '2025-12-27'")).scalar()
    
    return shopee_nov, tiktok_missing

def monitor():
    engine = create_engine(settings.DATABASE_URL)
    
    print("\n🚀 Starting Sync Monitor (Auto-Update)...")
    print(f"{'Time':<10} | {'Shopee (Nov)':<15} | {'TikTok (Dec/Jan)':<15} | {'Speed (trans/min)':<18}")
    print("-" * 70)
    
    last_shopee = 0
    last_tiktok = 0
    start_time = time.time()
    
    try:
        with engine.connect() as conn:
            # Initial count
            last_shopee, last_tiktok = get_counts(conn)
            
            while True:
                time.sleep(10) # Update every 10 seconds
                current_shopee, current_tiktok = get_counts(conn)
                
                shopee_diff = current_shopee - last_shopee
                tiktok_diff = current_tiktok - last_tiktok
                
                # Estimate speed (per minute)
                speed = (shopee_diff + tiktok_diff) * 6 
                
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"{current_time:<10} | {current_shopee:<15} | {current_tiktok:<15} | {speed:<18}")
                
                last_shopee = current_shopee
                last_tiktok = current_tiktok
                
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped.")

if __name__ == "__main__":
    monitor()
