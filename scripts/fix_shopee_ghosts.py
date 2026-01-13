import asyncio
import sys, os
from datetime import date
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.services.sync_service import OrderSyncService
from app.models import PlatformConfig, OrderHeader
from app.integrations.shopee import ShopeeClient
from sqlalchemy import cast, Date

async def fix_all_shopee_ghosts():
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

        # Find all Shopee orders shipped on Jan 3rd
        orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'shopee',
            cast(OrderHeader.shipped_at, Date) == '2026-01-03'
        ).all()
        
        print(f"Found {len(orders)} orders to fix...")
        
        fixed_count = 0
        for order in orders:
            try:
                # print(f"Fixing {order.external_order_id}...")
                detail = await client.get_order_detail(order.external_order_id)
                if not detail:
                    print(f"Failed to get detail for {order.external_order_id}")
                    continue

                normalized = client.normalize_order(detail)
                created, updated = sync_service._process_order(normalized, None)
                if updated:
                    fixed_count += 1
            except Exception as e:
                print(f"Error fixing {order.external_order_id}: {e}")
                
        print(f"Successfully fixed {fixed_count} orders.")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_all_shopee_ghosts())
