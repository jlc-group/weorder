#!/usr/bin/env python3
"""
Analyze potential reasons for "Slight Discrepancy" in Shipped Counts for Jan 8, 2026.
1. Check for orders that were shipped but later Cancelled/Returned (Excluded by current logic).
2. Check for Timezone boundary effects (UTC vs Local).
"""
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date, text

db = SessionLocal()

print("=== Analyzing Shipped Count Discrepancy (Jan 8, 2026) ===")

target_date = '2026-01-08'

# 1. Current Dashboard Logic (Clean Shipped)
current_count = db.query(func.count(OrderHeader.id)).filter(
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).scalar()

print(f"1. Current Dashboard 'Shipped' Count: {current_count:,}")

# 2. "Physically Shipped" but Cancelled/Returned
hidden_shipped = db.query(OrderHeader).filter(
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.in_(['CANCELLED', 'RETURNED'])
).all()

print(f"2. Hidden Shipped (Cancelled/Returned after ship): {len(hidden_shipped)}")
for o in hidden_shipped:
    print(f"   - {o.external_order_id} ({o.channel_code}) Status: {o.status_normalized}")

# 3. Timezone Edge Cases
# Check orders shipped between 00:00-07:00 UTC on Jan 9 (which is Jan 8 in specific TZ interpretation?)
# Wait, user is GMT+7. 
# DB stores UTC (presumably).
# If user selects Jan 8:
# Dashboard logic uses `range_start_utc` and `range_end_utc` derived from frontend "YYYY-MM-DD".
# The frontend sends "2026-01-08" to "2026-01-08".
# Backend `get_dashboard_stats`:
#   start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
#   end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
#   ...
#   range_end = end_date_obj + timedelta(days=1, microseconds=-1)
#   
#   Then convert to UTC?
#   If the backend assumes the input date is Local Time (GMT+7), then it converts to UTC range.
#   2026-01-08 00:00:00 BKK -> 2026-01-07 17:00:00 UTC
#   2026-01-08 23:59:59 BKK -> 2026-01-08 16:59:59 UTC
#
#   However, my previous scripts checked `cast(shipped_at, Date) == '2026-01-08'`.
#   Postgres CAST(... AS DATE) is immutable and depends on server timezone setting if timestamp is TZ-aware,
#   or just cuts off time if naive.
#
#   Let's check what the server Timezone is.

print("\n3. checking Server Timezone Config")
server_tz = db.execute(text("SHOW timezone")).scalar()
print(f"   DB Server Timezone: {server_tz}")

print("\n4. Counting with broad range (Jan 7 17:00 UTC to Jan 8 17:00 UTC)")
# Simulating strict GMT+7 window
start_utc = datetime(2026, 1, 7, 17, 0, 0)
end_utc = datetime(2026, 1, 8, 16, 59, 59)

strict_tz_count = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.shipped_at >= start_utc,
    OrderHeader.shipped_at <= end_utc,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).scalar()

print(f"   Strict UTC Window (GMT+7 based): {strict_tz_count:,}")
print(f"   Difference from CAST date: {strict_tz_count - current_count}")

print("\n5. Channel Breakdown of Current Count (2,925)")
breakdown = db.query(
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).filter(
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by(OrderHeader.channel_code).all()

for ch, cnt in breakdown:
    print(f"   {ch}: {cnt:,}")

print("\n6. Creation Date Breakdown of Current Count (2,925)")
creation_dist = db.query(
    func.to_char(OrderHeader.order_datetime, 'YYYY-MM').label('month'),
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).filter(
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by(
    'month',
    OrderHeader.channel_code
).order_by(
    'month',
    OrderHeader.channel_code
).all()

for month, ch, cnt in creation_dist:
    print(f"   Created {month} | {ch}: {cnt:,}")

db.close()
