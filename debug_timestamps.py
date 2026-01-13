import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.order import OrderHeader
from app.integrations.shopee import ShopeeClient
from app.integrations.tiktok import TikTokClient
from app.core import settings
from sqlalchemy import text
from datetime import datetime

async def inspect():
    db = SessionLocal()
    try:
        # Get one recent Shopee order with shipped_at
        print("\n--- Inspecting Shopee Order ---")
        shopee_order = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'shopee',
            OrderHeader.shipped_at.isnot(None),
            OrderHeader.status_normalized == 'DELIVERED'
        ).order_by(OrderHeader.order_datetime.desc()).first()

        if shopee_order:
            print(f"Order ID: {shopee_order.external_order_id}")
            print(f"DB Shipped At: {shopee_order.shipped_at}")
            
            # Check raw payload
            raw = shopee_order.raw_payload or {}
            print(f"Raw pickup_done_time: {raw.get('pickup_done_time')}")
            if raw.get('pickup_done_time'):
                ts = datetime.fromtimestamp(raw.get('pickup_done_time'))
                print(f"Converted Time: {ts}")
                
                if abs((ts - shopee_order.shipped_at).total_seconds()) < 60:
                     print("✅ DB value matches raw pickup_done_time")
                else:
                     print("❌ DB value mismatch!")
            else:
                print("⚠️ No pickup_done_time in raw_payload")
        
        # Get one recent TikTok order with shipped_at
        print("\n--- Inspecting TikTok Order ---")
        tiktok_order = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.shipped_at.isnot(None),
            OrderHeader.status_normalized == 'DELIVERED'
        ).order_by(OrderHeader.order_datetime.desc()).first()

        if tiktok_order:
            print(f"Order ID: {tiktok_order.external_order_id}")
            print(f"DB Shipped At: {tiktok_order.shipped_at}")
            
            # Check raw payload
            raw = tiktok_order.raw_payload or {}
            print(f"Raw collection_time: {raw.get('collection_time')}")
            if raw.get('collection_time'):
                ts = datetime.fromtimestamp(raw.get('collection_time') / 1000 if raw.get('collection_time') > 9999999999 else raw.get('collection_time'))
                print(f"Converted Time: {ts}")
                
                 # Note: TikTok might use ms or seconds, usually ms for new APIs
                print(f"Is Seconds? {raw.get('collection_time') < 9999999999}")
            else:
                print("⚠️ No collection_time in raw_payload")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(inspect())
