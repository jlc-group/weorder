
import asyncio
from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service
import json

async def check_lazada_jan5():
    db = SessionLocal()
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    client = integration_service.get_client_for_config(config)
    
    # Check Jan 5 (UTC range)
    # ICT Jan 5 00:00 - 23:59 -> UTC Jan 4 17:00 - Jan 5 17:00
    time_from = datetime(2026, 1, 4, 17, 0, tzinfo=timezone.utc)
    time_to = datetime(2026, 1, 5, 17, 0, tzinfo=timezone.utc)
    
    print(f"Checking Lazada orders created between {time_from} and {time_to} (ICT Jan 5)")
    
    # We'll fetch orders created on that day
    result = await client.get_orders(time_from=time_from, time_to=time_to)
    orders = result.get('orders', [])
    print(f"Total orders created on Jan 5 (ICT): {len(orders)}")
    
    status_counts = {}
    for o in orders:
        s = o.get('statuses', ['UNKNOWN'])[0]
        status_counts[s] = status_counts.get(s, 0) + 1
    
    print("Status Distribution in API:")
    print(json.dumps(status_counts, indent=2))
    
    # Check if any are 'shipped' or 'delivered' but recorded otherwise in DB
    shipped_in_api = [o for o in orders if o.get('statuses', [''])[0] in ['shipped', 'delivered']]
    print(f"Shipped/Delivered in API: {len(shipped_in_api)}")
    
    if shipped_in_api:
        sample = shipped_in_api[0]
        print("Sample Shipped Order:")
        print(json.dumps({
            'order_id': sample.get('order_id'),
            'status': sample.get('statuses'),
            'updated_at': sample.get('updated_at')
        }, indent=2))
        
    db.close()

if __name__ == "__main__":
    asyncio.run(check_lazada_jan5())
