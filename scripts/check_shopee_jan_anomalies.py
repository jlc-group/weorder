#!/usr/bin/env python3
"""
Diagnostic: Check Shopee for Jan 1-7, 2026.
"""
import sys
import os
from sqlalchemy import func, cast, Date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader

db = SessionLocal()
START_DATE = '2026-01-01'
END_DATE = '2026-01-07'

print("=== Shopee Diagnostic: Jan 1-7, 2026 ===")

# 1. Daily Shipped Counts
print("Daily Shipped Counts:")
daily_counts = db.query(
    cast(OrderHeader.shipped_at, Date).label('ship_date'),
    func.count(OrderHeader.id)
).filter(
    OrderHeader.channel_code == 'shopee',
    cast(OrderHeader.shipped_at, Date) >= START_DATE,
    cast(OrderHeader.shipped_at, Date) <= END_DATE,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by('ship_date').order_by('ship_date').all()

for d, c in daily_counts:
    print(f"  {d}: {c}")
    
# 2. Ghost Analysis (Backlog Clearing)
print("Backlog Analysis (Shipped Jan 1-7, Created < Jan 1):")
ghost_stats = db.query(
    cast(OrderHeader.shipped_at, Date).label('ship_date'),
    func.count(OrderHeader.id)
).filter(
    OrderHeader.channel_code == 'shopee',
    cast(OrderHeader.shipped_at, Date) >= START_DATE,
    cast(OrderHeader.shipped_at, Date) <= END_DATE,
    OrderHeader.order_datetime < '2026-01-01', # Created in 2025
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by('ship_date').order_by('ship_date').all()

total_ghosts = 0
for d, c in ghost_stats:
    print(f"  {d}: {c} orders from 2025")
    total_ghosts += c
        
print(f"  Total Backlog Orders Cleared: {total_ghosts}")

db.close()
