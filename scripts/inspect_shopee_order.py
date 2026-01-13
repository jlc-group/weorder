import sys
import os
import asyncio
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.integrations.shopee import ShopeeClient

async def inspect():
    db = SessionLocal()
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'shopee').first()
    
    client = ShopeeClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    order_sn = "251230P5AVDDMG"
    print(f"Fetching details for {order_sn}...")
    
    # Use the batch method (list) or detail
    # get_order_detail returns a single dict
    res = await client.get_order_detail(order_sn)
    
    print("--- Raw Response (Relevant Fields) ---")
    print(f"order_status: {res.get('order_status')}")
    print(f"create_time: {res.get('create_time')}")
    print(f"update_time: {res.get('update_time')}")
    print(f"pickup_done_time: {res.get('pickup_done_time')}")
    print(f"shipping_carrier: {res.get('shipping_carrier')}")
    
    if res.get('pickup_done_time'):
        import datetime
        dt = datetime.datetime.fromtimestamp(res['pickup_done_time'])
        print(f"✅ VALID PICKUP TIME: {dt}")
    else:
        print("❌ NO PICKUP TIME")

    db.close()

if __name__ == "__main__":
    asyncio.run(inspect())
