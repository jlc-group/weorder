#!/usr/bin/env python3
"""
Investigate Lazada Rollover Orders.
Orders marked as Shipped in Dec 2025, but updated in Jan 2026.
Maybe they were 'Ready to Ship' in Dec, but actually Shipped in Jan?
"""
import sys
import os
from sqlalchemy import func, cast, Date
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader

db = SessionLocal()

print("=== Analyzing Lazada Dec->Jan Rollover ===")

# Count orders shipped in Dec 2025 but updated in Jan 2026
rollovers = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.channel_code == 'lazada',
    OrderHeader.shipped_at < '2026-01-01',
    OrderHeader.updated_at >= '2026-01-01',
    OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED'])
).scalar()

print(f"Orders Shipped < Jan 1 but Updated >= Jan 1: {rollovers}")

# If significant, breakdown by "Shipped Date"
if rollovers > 0:
    print("\nBreakdown by Shipped Date (Dec 2025):")
    dist = db.query(
        cast(OrderHeader.shipped_at, Date).label('sdate'),
        func.count(OrderHeader.id)
    ).filter(
        OrderHeader.channel_code == 'lazada',
        OrderHeader.shipped_at < '2026-01-01',
        OrderHeader.updated_at >= '2026-01-01',
        OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED'])
    ).group_by('sdate').order_by('sdate').all()
    
    for d, c in dist:
        print(f"  {d}: {c}")

db.close()
