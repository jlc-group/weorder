import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings, engine
from sqlalchemy.orm import sessionmaker
from app.models.integration import PlatformConfig
from app.integrations.shopee import ShopeeClient

async def check_api_counts():
    print("Checking 'To Ship' counts directly from Shopee API...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'shopee',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("Error: No active Shopee configuration found.")
            return

        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        # Check last 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # 1. Count READY_TO_SHIP
        msg_rts, count_rts = await count_status(client, 'READY_TO_SHIP', start_date, end_date)
        print(f"READY_TO_SHIP: {count_rts} orders")
        
        # 2. Count PROCESSED
        msg_proc, count_proc = await count_status(client, 'PROCESSED', start_date, end_date)
        print(f"PROCESSED: {count_proc} orders")
        
        total = count_rts + count_proc
        print("-" * 30)
        print(f"Total 'To Ship' (API): {total}")
        print("==============================")
        
    finally:
        db.close()

async def count_status(client, status, start_date, end_date):
    total_count = 0
    current_start = start_date
    
    # Loop in 15-day chunks to be safe
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=15), end_date)
        
        cursor = ""
        while True:
            try:
                res = await client.get_orders(
                    status=status,
                    cursor=cursor,
                    page_size=100, # Max page size
                    time_from=current_start,
                    time_to=current_end
                )
                
                orders = res.get("orders", [])
                total_count += len(orders)
                
                if not res.get("has_more"):
                    break
                    
                cursor = res.get("next_cursor")
                if not cursor:
                    break
                    
            except Exception as e:
                print(f"Error counting {status}: {e}")
                break
        
        current_start = current_end
        
    return status, total_count

if __name__ == "__main__":
    asyncio.run(check_api_counts())
