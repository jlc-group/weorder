#!/usr/bin/env python3
"""
Breakdown Jan 8 Shipped Orders by Creation Date (Day).
To prove the "Backlog Clearing" hypothesis.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date

db = SessionLocal()

print("=== Breakdown of Jan 8 Shipments by Creation Day ===")
target_date = '2026-01-08'

# Query
results = db.query(
    cast(OrderHeader.order_datetime, Date).label('create_date'),
    func.count(OrderHeader.id)
).filter(
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by('create_date').order_by('create_date').all()

total_shipped = 0
created_on_jan8 = 0
backlog = 0

for date, count in results:
    print(f"Created on {date}: {count:,}")
    total_shipped += count
    if str(date) == target_date:
        created_on_jan8 += count
    elif str(date) < target_date:
        backlog += count

print("-" * 30)
print(f"Total Shipped on Jan 8: {total_shipped:,}")
print(f"  - Created & Shipped Same Day (Jan 8): {created_on_jan8:,}")
print(f"  - Backlog Cleared (Created < Jan 8): {backlog:,}")

db.close()
