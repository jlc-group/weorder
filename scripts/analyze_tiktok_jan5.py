#!/usr/bin/env python3
"""
Analyze TikTok Jan 5 Anomalies by Creation Date.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date

db = SessionLocal()

print("=== Analyzing TikTok Jan 5 Age Distribution ===")
target_date = '2026-01-05'

# Group by Create Year-Month
results = db.query(
    func.to_char(OrderHeader.order_datetime, 'YYYY-MM').label('create_month'),
    func.count(OrderHeader.id)
).filter(
    OrderHeader.channel_code == 'tiktok',
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by('create_month').order_by('create_month').all()

total = 0
for month, count in results:
    print(f"Created in {month}: {count:,}")
    total += count

print(f"Total Shipped on Jan 5: {total:,}")
db.close()
