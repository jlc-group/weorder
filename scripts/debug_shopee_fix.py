import asyncio
import sys, os
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.services.sync_service import OrderSyncService
from app.models import PlatformConfig, OrderHeader
from app.integrations.shopee import ShopeeClient

async def fix_shopee_ghost_order():
    db = SessionLocal()
    try:
        # Get Shopee config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "shopee", PlatformConfig.is_active == True).first()
        if not config:
            print("Shopee config not found")
            return

        sync_service = OrderSyncService(db)
        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
        )

        target_order_sn = "250217DRXK913H" 
        
        print(f"Fetching detail for {target_order_sn}...")
        detail = await client.get_order_detail(target_order_sn)
        if not detail:
            print("Failed to get order detail")
            return
            
        print(f"Raw Pickup Time: {detail.get('pickup_done_time')}")

        normalized = client.normalize_order(detail)
        print(f"Normalized Shipped At: {normalized.shipped_at}")
        
        # Manually invoke process order
        created, updated = sync_service._process_order(normalized, None)
        print(f"Sync Result: updated={updated}")
        
        # Verify DB
        db.expire_all()
        order = db.query(OrderHeader).filter(OrderHeader.external_order_id == target_order_sn).first()
        print(f"DB Shipped At After Sync: {order.shipped_at}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_shopee_ghost_order())
