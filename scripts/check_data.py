from app.core.database import SessionLocal
from app.models import OrderHeader
from sqlalchemy import func, and_
from datetime import datetime, time

db = SessionLocal()

# Date: 2026-01-08
target_date = datetime(2026, 1, 8)
start_dt = datetime.combine(target_date, time.min)
end_dt = datetime.combine(target_date, time.max)

print('=' * 60)
print(f'Checking data for: {target_date.date()}')
print('=' * 60)

# 1. Check collection_time counts per platform
print('\n[1] Orders with collection_time on this date:')
collection_results = db.query(
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).filter(
    OrderHeader.collection_time >= start_dt,
    OrderHeader.collection_time <= end_dt
).group_by(OrderHeader.channel_code).all()

total_collection = 0
for platform, count in collection_results:
    print(f'  {platform}: {count}')
    total_collection += count
print(f'  TOTAL: {total_collection}')

# 2. Check shipped_at counts per platform (as comparison)
print('\n[2] Orders with shipped_at on this date:')
shipped_results = db.query(
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).filter(
    OrderHeader.shipped_at >= start_dt,
    OrderHeader.shipped_at <= end_dt
).group_by(OrderHeader.channel_code).all()

total_shipped = 0
for platform, count in shipped_results:
    print(f'  {platform}: {count}')
    total_shipped += count
print(f'  TOTAL: {total_shipped}')

# 3. Check RTS orders (rts_time) - packed but maybe not collected
print('\n[3] Orders with rts_time on this date (packed/prepared):')
rts_results = db.query(
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).filter(
    OrderHeader.rts_time >= start_dt,
    OrderHeader.rts_time <= end_dt
).group_by(OrderHeader.channel_code).all()

total_rts = 0
for platform, count in rts_results:
    print(f'  {platform}: {count}')
    total_rts += count
print(f'  TOTAL: {total_rts}')

# 4. Check how many orders have NULL collection_time vs non-null
print('\n[4] Overall collection_time coverage:')
total_orders = db.query(func.count(OrderHeader.id)).scalar()
with_collection = db.query(func.count(OrderHeader.id)).filter(OrderHeader.collection_time.isnot(None)).scalar()
pct = (100*with_collection/total_orders) if total_orders else 0
print(f'  Total orders in DB: {total_orders}')
print(f'  With collection_time: {with_collection} ({pct:.1f}%)')
print(f'  Without collection_time: {total_orders - with_collection}')

# 5. Expected vs Actual
print('\n[5] Expected counts from factory:')
print('  Shopee: 390')
print('  TikTok: 2400')
print('  Lazada: 35')
print('  TOTAL: 2825')

db.close()
