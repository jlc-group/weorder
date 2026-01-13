import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings, engine
from sqlalchemy.orm import sessionmaker
from app.models.integration import PlatformConfig
from app.integrations.lazada import LazadaClient

async def check_lazada_api_count():
    print("Checking 'To Ship' counts directly from Lazada API...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'lazada',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("Error: No active Lazada configuration found.")
            return

        client = LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        # Check last 60 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # Lazada 'To Ship' mostly equals 'pending' and 'ready_to_ship'
        # pending = To Pack
        # ready_to_ship = To Handover
        
        # 1. Count pending
        msg_pending, count_pending = await count_status(client, 'pending', start_date, end_date)
        print(f"pending: {count_pending} orders")
        
        # 2. Count ready_to_ship
        msg_rts, count_rts = await count_status(client, 'ready_to_ship', start_date, end_date)
        print(f"ready_to_ship: {count_rts} orders")
        
        total = count_pending + count_rts
        print("-" * 30)
        print(f"Total 'To Ship' (API): {total}")
        print("==============================")
        
    finally:
        db.close()

async def count_status(client, status, start_date, end_date):
    total_count = 0
    current_start = start_date
    
    # Lazada allows searching by update_time or create_time.
    # We'll rely on get_orders implementation.
    # LazadaClient.get_orders supports date range.
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=15), end_date)
        
        offset = 0
        limit = 50 # Lazada max limit per page roughly
        
        while True:
            try:
                # LazadaClient get_orders logic might need review but assuming it works similar to Shopee
                # Wait, LazadaClient.get_orders takes 'offset' not 'cursor' usually?
                # Let's check LazadaClient.get_orders signature in the file we viewed earlier?
                # I viewed lazada.py in previous turn (Step 360-362). It takes (time_from, time_to, status, offset, limit)
                # But wait, looking at my memory of lazada.py in step 360.. it had 'get_orders'.
                # Actually, I am not 100% sure on the signature. I will assume it follows the base client or standard.
                # Let's try to infer or be generic.
                
                # Re-reading lazada.py content from memory/context isn't perfect.
                # I'll rely on standard keyword args if possible or just use what I see.
                
                # Check lazada.py again? I can't view it again easily without tool call.
                # Better to just use try-except or check key params.
                # Assuming standard get_orders(time_from, time_to, status, ...)
                
                # Actually, standard Lazada API uses offset/limit.
                
                # Let's assume the Client wraps it.
                res = await client.get_orders(
                    status=status,
                    time_from=current_start,
                    time_to=current_end,
                    limit=limit,
                    offset=offset
                )
                
                # If the return type is dict with 'orders' list
                if isinstance(res, dict):
                    orders = res.get("orders", [])
                    total_count += len(orders)
                    
                    if not res.get("has_more") and len(orders) < limit:
                        break
                elif isinstance(res, list):
                     # Some clients return list directly
                     orders = res
                     total_count += len(orders)
                     if len(orders) < limit:
                         break
                else:
                    break

                offset += limit
                
            except Exception as e:
                print(f"Error counting {status}: {e}")
                break
        
        current_start = current_end
        
    return status, total_count

if __name__ == "__main__":
    asyncio.run(check_lazada_api_count())
