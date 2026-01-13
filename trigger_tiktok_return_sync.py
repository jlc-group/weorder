
import asyncio
print("DEBUG: asyncio imported")
import os
print("DEBUG: os imported")
import sys
from datetime import datetime, timedelta
print("DEBUG: standard libs imported")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
print("DEBUG: SessionLocal imported")
from app.services.sync_service import OrderSyncService
print("DEBUG: OrderSyncService imported")
from app.models.integration import PlatformConfig
print("DEBUG: PlatformConfig imported")
from app.models.order import OrderHeader
print("DEBUG: OrderHeader imported")

async def verify_sync():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'tiktok', PlatformConfig.is_active == True).first()
        if not config:
            print("No active TikTok config found")
            return

        print(f"Triggering Return Sync for {config.shop_name}...")
        service = OrderSyncService(db)
        
        # Test order we know is returned: 581932196284761716
        # Let's check its status before
        order_id = "581932196284761716"
        order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
        if order:
            print(f"Before Sync: {order_id} | Status: {order.status_normalized} | Raw: {order.status_raw}")
        else:
            print(f"Order {order_id} not found in DB. Running regular sync first?")
            # Maybe run regular sync first for a short period?
            # await service.sync_platform_orders(config, time_from=datetime.utcnow()-timedelta(days=30))
            # order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
        
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=60)
        
        # Call sync_platform_orders which now includes sync_returns
        stats = await service.sync_platform_orders(config, time_from=time_from, time_to=time_to)
        print(f"Sync Results: {stats}")
        
        # Final check
        db.expire_all()
        order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
        if order:
            print(f"After Sync: {order_id} | Status: {order.status_normalized} | Raw: {order.status_raw}")
        
        # Check if any order became RETURNED
        returned_orders = db.query(OrderHeader).filter(OrderHeader.platform == 'tiktok', OrderHeader.status_normalized == 'RETURNED').all()
        print(f"Total TikTok RETURNED orders: {len(returned_orders)}")
        for o in returned_orders[:5]:
            print(f"  - {o.external_order_id}: {o.status_raw}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_sync())
