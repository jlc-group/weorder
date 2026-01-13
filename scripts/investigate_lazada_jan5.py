#!/usr/bin/env python3
"""
Investigate Lazada Jan 5 Data Anomaly.
Check for orders that SHOULD have been shipped on Jan 5.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date

db = SessionLocal()

print("=== Analyzing Lazada Jan 5 Data ===")
target_date = '2026-01-05'

# 1. Official Shipped Count (Jan 5 & 6)
count_jan5 = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.channel_code == 'lazada',
    cast(OrderHeader.shipped_at, Date) == '2026-01-05',
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).scalar()

count_jan6 = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.channel_code == 'lazada',
    cast(OrderHeader.shipped_at, Date) == '2026-01-06',
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).scalar()

print(f"Current Dashboard Shipped Count - Jan 5: {count_jan5}")
print(f"Current Dashboard Shipped Count - Jan 6: {count_jan6}")

# 2. Check Activity around Jan 5
# Look for orders UPDATED on Jan 5 but having different shipped_at
updated_on_jan5 = db.query(
    OrderHeader.status_normalized,
    cast(OrderHeader.shipped_at, Date).label('ship_date'),
    func.count(OrderHeader.id)
).filter(
    OrderHeader.channel_code == 'lazada',
    cast(OrderHeader.updated_at, Date) == target_date
).group_by(
    'status_normalized', 'ship_date'
).all()

print("\nOrders Updated on Jan 5 (Status / Shipped Date):")
for status, ship_date, count in updated_on_jan5:
    print(f"  {status} | Shipped: {ship_date} | Count: {count}")

# 3. Check for specific orders that might be candidates (Created early Jan, Status Shipped/Delivered, no Ship Date)
candidates = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.channel_code == 'lazada',
    OrderHeader.order_datetime >= '2026-01-01',
    OrderHeader.order_datetime <= '2026-01-05',
    OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED']),
    OrderHeader.shipped_at.is_(None)
).scalar()

print(f"\nPotential Candidates (Created Jan 1-5, Shipped/Delivered, but No Shipped Date): {candidates}")

db.close()
