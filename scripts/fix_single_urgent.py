from app.core import SessionLocal
from app.models import OrderHeader
from app.integrations.tiktok import TikTokClient
from app.integrations.shopee import ShopeeClient
from app.integrations.lazada import LazadaClient
from app.services import integration_service
from datetime import datetime, timezone
import asyncio

async def fix_one():
    db = SessionLocal()
    order_id = "579824638121184088"
    print(f"Fixing {order_id}...")
    
    order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
    if not order:
        print("Order not found")
        return

    # Get Config
    configs = integration_service.get_platform_configs(db, platform='tiktok', is_active=True)
    client = integration_service.get_client_for_config(configs[0])
    
    # Get Detail
    detail_list = await client.get_order_details_batch([order_id])
    detail = detail_list[0]
    
    ts = int(detail.get("collection_time") or detail.get("rts_time") or 0)
    print(f"Raw TS: {ts}")
    
    if ts > 10000000000:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        
    print(f"Correct Date: {dt}")
    
    order.shipped_at = dt
    db.commit()
    print("Saved.")
    db.close()

if __name__ == "__main__":
    asyncio.run(fix_one())
