#!/usr/bin/env python3
"""
Master Diagnostic: Check All Platforms for Jan 1-7, 2026 Anomalies.
1. Daily Shipped Counts.
2. 'Ghost' Analysis: Orders Shipped in Jan 1-7 but Created < Jan 1, 2026.
   (This indicates backlog clearing).
"""
import sys
import os
from sqlalchemy import func, cast, Date, case
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader

db = SessionLocal()

PLATFORMS = ['shopee', 'lazada', 'tiktok']
START_DATE = '2026-01-01'
END_DATE = '2026-01-07'

print(f"=== Master Diagnostic: Jan 1-7, 2026 ===")

for platform in PLATFORMS:
    print(f"\n--- {platform.upper()} ---")
    
    # 1. Daily Shipped Counts
    print("Daily Shipped Counts:")
    daily_counts = db.query(
        cast(OrderHeader.shipped_at, Date).label('ship_date'),
        func.count(OrderHeader.id)
    ).filter(
        OrderHeader.channel_code == platform,
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
        OrderHeader.channel_code == platform,
        cast(OrderHeader.shipped_at, Date) >= START_DATE,
        cast(OrderHeader.shipped_at, Date) <= END_DATE,
        OrderHeader.order_datetime < '2026-01-01', # Created in 2025
        OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
    ).group_by('ship_date').order_by('ship_date').all()
    
    total_ghosts = 0
    if not ghost_stats:
        print("  No backlog clearing detected (0 orders created in 2025).")
    else:
        for d, c in ghost_stats:
            print(f"  {d}: {c} orders from 2025")
            total_ghosts += c
            
    print(f"  Total Backlog Orders Cleared: {total_ghosts}")

db.close()
