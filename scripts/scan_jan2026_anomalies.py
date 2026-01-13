#!/usr/bin/env python3
"""
Scan January 2026 for Data Anomalies.
Identifies "Ghost Shipments": Orders marked as shipped in Jan 2026
but created significantly earlier (e.g., in 2025).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import func, cast, Date, case

db = SessionLocal()

print("=== Scanning Jan 2026 for 'Ghost Shipments' (Backlog Flooding) ===")
print("Criteria: Shipped in Jan 2026 BUT Created before Jan 1, 2026")
print(f"{'Shipped Date':<15} | {'Channel':<10} | {'Ghost Count':<12} | {'Total Shipped':<12} | {'% Ghosts':<10}")
print("-" * 70)

# Query logic: Group by shipped_at date and channel, count distinct anomalies
results = db.query(
    cast(OrderHeader.shipped_at, Date).label('ship_date'),
    OrderHeader.channel_code,
    func.count(OrderHeader.id).label('total_count'),
    func.sum(
        case(
            (OrderHeader.order_datetime < '2026-01-01', 1),
            else_=0
        )
    ).label('ghost_count')
).filter(
    cast(OrderHeader.shipped_at, Date) >= '2026-01-01',
    cast(OrderHeader.shipped_at, Date) <= '2026-01-31',
    OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
).group_by(
    'ship_date', 
    OrderHeader.channel_code
).order_by(
    'ship_date', 
    OrderHeader.channel_code
).all()

anomalies_found = False

for r in results:
    ship_date = r.ship_date
    channel = r.channel_code
    total = r.total_count
    ghosts = r.ghost_count or 0
    
    # Flag significant anomalies (> 10% or > 50 orders)
    is_anomaly = (ghosts > 50) or (ghosts / total > 0.1 if total > 0 else False)
    
    if is_anomaly:
        anomalies_found = True
        pct = (ghosts / total * 100) if total > 0 else 0
        print(f"{str(ship_date):<15} | {channel:<10} | {ghosts:<12,} | {total:<12,} | {pct:>.1f}% 🚩")
    # else:
    #     print(f"{str(ship_date):<15} | {channel:<10} | {ghosts:<12,} | {total:<12,} | -")

if not anomalies_found:
    print("\n✅ No significant ghost shipment anomalies found in other days.")
else:
    print("\n⚠️ Anomalies detected! Recommend running cleanup for the flagged days.")

db.close()
