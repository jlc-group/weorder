import asyncio
import sys, os
sys.path.append(os.getcwd())

from app.core import SessionLocal, settings
from app.services.sync_service import OrderSyncService
from app.models import PlatformConfig
from app.integrations.lazada import LazadaClient

async def test_single_order_sync():
    db = SessionLocal()
    try:
        # Get Lazada config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "lazada", PlatformConfig.is_active == True).first()
        if not config:
            print("Lazada config not found")
            return

        sync_service = OrderSyncService(db)
        client = LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
        )

        # Target order ID from previous check
        target_order_id = "1074255913052684" 
        
        print(f"Syncing order {target_order_id}...")
        detail = await client.get_order_detail(target_order_id)
        if not detail:
            print("Failed to get order detail")
            return
            
        if "order_items" in detail:
            print(f"Found {len(detail['order_items'])} items in detail")
        else:
            print("Items NOT found in detail")

        normalized = client.normalize_order(detail)
        created, updated = sync_service._process_order(normalized, None)
        
        print(f"Process result: created={created}, updated={updated}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_single_order_sync())
