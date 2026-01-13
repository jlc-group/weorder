
import asyncio
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service
import json

async def verify_lazada(db):
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    if not config:
        print("Lazada config not found")
        return
    
    client = integration_service.get_client_for_config(config)
    
    # Fetch orders updated between Jan 4 and Jan 6
    time_from = datetime(2026, 1, 4)
    time_to = datetime(2026, 1, 7)
    
    print(f"Fetching Lazada orders from {time_from} to {time_to}...")
    result = await client.get_orders(time_from=time_from, time_to=time_to)
    orders = result.get('orders', [])
    print(f"Found {len(orders)} orders in Lazada API")
    
    samples = []
    for o in orders[:20]:
        # Extract status and update time
        samples.append({
            'id': o.get('order_id'),
            'status': o.get('statuses'),
            'created_at': o.get('created_at'),
            'updated_at': o.get('updated_at')
        })
    
    print("Lazada Samples (first 20):")
    print(json.dumps(samples, indent=2))

async def verify_shopee(db):
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'shopee', PlatformConfig.is_active == True).first()
    if not config: return
    client = integration_service.get_client_for_config(config)
    
    time_from = datetime(2026, 1, 4)
    time_to = datetime(2026, 1, 7)
    
    print(f"Fetching Shopee orders from {time_from} to {time_to}...")
    # Shopee get_orders returns IDs, then we need detail
    result = await client.get_orders(time_from=time_from, time_to=time_to)
    order_sns = [o.get('order_sn') for o in result.get('orders', [])]
    print(f"Found {len(order_sns)} orders in Shopee API")
    
    if order_sns:
        detail = await client.get_order_detail(order_sns[0])
        print("Shopee Sample (first):")
        print(json.dumps(detail, indent=2))

async def main():
    db = SessionLocal()
    await verify_lazada(db)
    await verify_shopee(db)
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
