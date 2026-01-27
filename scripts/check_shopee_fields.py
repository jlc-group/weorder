import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models import OrderHeader

db = SessionLocal()

# Get a Shopee SHIPPED order with raw_payload
shopee = db.query(OrderHeader).filter(
    OrderHeader.channel_code == 'shopee',
    OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED'])
).first()

if shopee:
    raw = shopee.raw_payload or {}
    print('Shopee raw_payload keys:')
    print(list(raw.keys()))
    print()
    print('Time-related fields:')
    for k in ['ship_by_date', 'update_time', 'create_time', 'days_to_ship', 'pickup_done_time']:
        print(f'{k}: {raw.get(k)}')
else:
    print('No Shopee order found')

db.close()
