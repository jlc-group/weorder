
import asyncio
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.tiktok import TikTokClient

async def main():
    load_dotenv()
    
    app_key = os.getenv("TIKTOK_APP_KEY")
    app_secret = os.getenv("TIKTOK_APP_SECRET")
    access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
    shop_id = os.getenv("TIKTOK_SHOP_ID")
    
    if not all([app_key, app_secret, access_token, shop_id]):
        print("Missing TikTok credentials in .env")
        return

    client = TikTokClient(
        app_key=app_key,
        app_secret=app_secret,
        shop_id=shop_id,
        access_token=access_token
    )
    
    print("Testing TikTok Returns/Cancellations Sync...")
    
    # Test time range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    try:
        # This calls both returns/search and cancellations/search (POST requests)
        result = await client.get_reverse_orders(
            update_time_from=start_date,
            update_time_to=end_date,
            page_size=10
        )
        
        returns = result.get("returns", [])
        print(f"✅ Success! Found {len(returns)} reverse orders.")
        for r in returns:
            print(f" - {r.get('return_order_id') or r.get('cancel_order_id')}: {r.get('return_status')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
