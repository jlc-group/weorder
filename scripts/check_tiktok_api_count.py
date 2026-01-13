import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings, engine
from sqlalchemy.orm import sessionmaker
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient

async def check_tiktok_api_count():
    print("Checking 'To Ship' counts directly from TikTok API...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("Error: No active TikTok configuration found.")
            return

        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        # Check last 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # TikTok 'To Ship' mapped to AWAITING_SHIPMENT and AWAITING_COLLECTION
        
        # 1. Count AWAITING_SHIPMENT
        msg_shp, count_shp = await count_status(client, 'AWAITING_SHIPMENT', start_date, end_date)
        print(f"AWAITING_SHIPMENT: {count_shp} orders")
        
        # 2. Count AWAITING_COLLECTION
        msg_col, count_col = await count_status(client, 'AWAITING_COLLECTION', start_date, end_date)
        print(f"AWAITING_COLLECTION: {count_col} orders")
        
        total = count_shp + count_col
        print("-" * 30)
        print(f"Total 'To Ship' (API): {total}")
        print("==============================")
        
    finally:
        db.close()

async def count_status(client, status, start_date, end_date):
    total_count = 0
    current_start = start_date
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=15), end_date)
        
        cursor = ""
        while True:
            try:
                res = await client.get_orders(
                    status=status,
                    cursor=cursor,
                    page_size=50,
                    time_from=current_start,
                    time_to=current_end
                )
                
                orders = res.get("orders", [])
                total_count += len(orders)
                
                # Check has_more and next_cursor
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
    asyncio.run(check_tiktok_api_count())
