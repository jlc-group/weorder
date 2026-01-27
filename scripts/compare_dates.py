import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models import OrderHeader
from datetime import datetime, time

db = SessionLocal()
date21 = datetime(2026, 1, 21)
start21 = datetime.combine(date21, time.min)
end21 = datetime.combine(date21, time.max)

print('=== Comparison: rts_time vs collection_time for 21/01 ===')
print('(rts_time = packed/label printed, collection_time = courier pickup)')
print('')

for p in ['shopee', 'tiktok', 'lazada']:
    rts = db.query(OrderHeader).filter(
        OrderHeader.channel_code == p,
        OrderHeader.rts_time >= start21,
        OrderHeader.rts_time <= end21
    ).count()
    col = db.query(OrderHeader).filter(
        OrderHeader.channel_code == p,
        OrderHeader.collection_time >= start21,
        OrderHeader.collection_time <= end21
    ).count()
    print(f'{p:8}: rts_time={rts:5}, collection_time={col:5}')

print('')
expected = {'shopee': 470, 'tiktok': 2505, 'lazada': 27}
print('=== Match with user expected data? ===')
for p in ['shopee', 'tiktok', 'lazada']:
    rts = db.query(OrderHeader).filter(
        OrderHeader.channel_code == p,
        OrderHeader.rts_time >= start21,
        OrderHeader.rts_time <= end21
    ).count()
    diff = rts - expected[p]
    status = '✓' if abs(diff) < 5 else '✗'
    print(f'{p}: rts_time={rts} vs user={expected[p]} (diff={diff:+d}) {status}')

db.close()
