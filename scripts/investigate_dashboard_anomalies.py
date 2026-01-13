#!/usr/bin/env python3
"""
Investigate Dashboard Anomalies:
1. Low-level analysis of the 33,031 "Shipped" orders on Jan 8.
   - When were they created? (Are they old backlog?)
   - Which channel?
   
2. Analysis of the 15,798 "Pending Review" (NEW) orders.
   - How old are they?
   - Which channel?
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date, desc

db = SessionLocal()

print("=== 1. Investigating 'Shipped' Orders on Jan 8, 2026 ===")
# Count shipped_at on Jan 8
shipped_date = '2026-01-08'
shipped_query = db.query(OrderHeader).filter(
    cast(OrderHeader.shipped_at, Date) == shipped_date,
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
)

total_shipped = shipped_query.count()
print(f"Total Shipped on {shipped_date}: {total_shipped:,}")

if total_shipped > 0:
    print("\n[Creation Date Distribution of Shipped Orders]")
    # Group by creation month
    dist = db.query(
        func.to_char(OrderHeader.order_datetime, 'YYYY-MM').label('month'),
        func.count(OrderHeader.id)
    ).filter(
        cast(OrderHeader.shipped_at, Date) == shipped_date,
        OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
    ).group_by('month').order_by('month').all()
    
    for month, count in dist:
        print(f"  Created in {month}: {count:,}")
        
    print("\n[Channel Distribution]")
    ch_dist = db.query(
        OrderHeader.channel_code,
        func.count(OrderHeader.id)
    ).filter(
        cast(OrderHeader.shipped_at, Date) == shipped_date,
        OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
    ).group_by(OrderHeader.channel_code).all()
    
    for ch, count in ch_dist:
        print(f"  {ch}: {count:,}")

print("\n" + "="*50 + "\n")

print("=== 2. Investigating 'Pending Review' (NEW) Orders ===")
new_query = db.query(OrderHeader).filter(OrderHeader.status_normalized == 'NEW')

total_new = new_query.count()
print(f"Total Pending (NEW): {total_new:,}")

if total_new > 0:
    print("\n[Age Distribution of Pending Orders]")
    # Group by creation month
    age_dist = db.query(
        func.to_char(OrderHeader.order_datetime, 'YYYY-MM').label('month'),
        func.count(OrderHeader.id)
    ).filter(
        OrderHeader.status_normalized == 'NEW'
    ).group_by('month').order_by('month').all()
    
    for month, count in age_dist:
        print(f"  Created in {month}: {count:,}")

    print("\n[Channel Distribution]")
    ch_dist = db.query(
        OrderHeader.channel_code,
        func.count(OrderHeader.id)
    ).filter(
        OrderHeader.status_normalized == 'NEW'
    ).group_by(OrderHeader.channel_code).all()
    
    for ch, count in ch_dist:
        print(f"  {ch}: {count:,}")

db.close()
