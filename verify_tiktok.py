import asyncio
import os
import sys

# Setup environment
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient
from datetime import datetime, timedelta

# DB Setup
# Use DATABASE_URL from settings or construct it
db_url = getattr(settings, "DATABASE_URL", None)
if not db_url:
    # Fallback to constructing it if individual fields exist
    db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def verify_tiktok_count():
    db = SessionLocal()
    try:
        # Get TikTok Config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "tiktok", PlatformConfig.is_active == True).first()
        if not config:
            print("❌ No active TikTok configuration found.")
            return

        print(f"✅ Found TikTok Config: Shop ID {config.shop_id}")
        
        # Initialize Client
        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        # Set cipher if available (V2 specific) - It seems not stored in PlatformConfig directly
        # If needed, it might be derived or hardcoded, but let's try without it first as SyncService does.
        # if config.extra_data and "shop_cipher" in config.extra_data:
        #      client.shop_cipher = config.extra_data["shop_cipher"]

        # Parameters for verification
        status_to_check = "AWAITING_SHIPMENT"
        days_back = 60
        time_from = datetime.utcnow() - timedelta(days=days_back)
        
        print(f"🔍 Fetching orders from TikTok API...")
        print(f"   - Status: {status_to_check}")
        print(f"   - Time Range: Last {days_back} days (From {time_from.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        
        # Call API
        total_count = 0
        cursor = None
        has_more = True
        page = 1
        
        while has_more:
            print(f"   ⏳ Fetching page {page}...", end="\r")
            result = await client.get_orders(
                time_from=time_from,
                status=status_to_check,
                cursor=cursor,
                page_size=50
            )
            
            orders = result.get("orders", [])
            # STRICT LOCAL FILTERING
            valid_orders = []
            for order in orders:
                # Debug status if needed
                # print(f"DEBUG ORDER: {order.get('id')} - {order.get('status')}")
                if order.get("status") == status_to_check:
                    valid_orders.append(order)
            
            count = len(valid_orders)
            total_count += count
            
            # Print first 5 statuses
            if page == 1 and orders:
                print("\n🔍 Sample Orders Statuses:")
                for i, o in enumerate(orders[:5]):
                    print(f"   {i+1}. ID: {o.get('id')} | Status: {o.get('status')}")
                
            has_more = result.get("more", False)
            cursor = result.get("cursor")
            page += 1
            
            if page == 1:
                print(f"   📊 API Claims Total Orders: {result.get('total')}")

            # Limit pages for debugging - Safety limit
            # if page > 10: 
            #    print("\n⚠️ Stopping early after 10 pages for safety...")
            #    break
            
            # Simple rate limit prevention
            await asyncio.sleep(0.5)

        print(f"\n✅ Total '{status_to_check}' orders from TikTok API: {total_count}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_tiktok_count())
