#!/usr/bin/env python3
"""
Fix Lazada Jan 5 Timestamps.
The re-sync set 'shipped_at' to NOW (Jan 10) for old orders.
We need to move them back to their payload 'updated_at' date.
"""
import sys
import os
from datetime import datetime, timezone
from dateutil import parser
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import cast, Date

db = SessionLocal()

print("=== Analyzing Lazada Orders Shipped on Jan 10 (Potential Ghosts) ===")
# Look for orders shipped today (Jan 10) but created earlier
target_ship_date = datetime.now().strftime('%Y-%m-%d') # Today
# OR just hardcode '2026-01-10' as that's when I ran the sync
target_ship_date = '2026-01-10'

candidates = db.query(OrderHeader).filter(
    OrderHeader.channel_code == 'lazada',
    cast(OrderHeader.shipped_at, Date) == target_ship_date,
    OrderHeader.order_datetime < '2026-01-09' # Created before yesterday
).all()

print(f"Found {len(candidates)} candidates shipped on {target_ship_date} but created earlier.")

to_fix = []
for order in candidates:
    raw = order.raw_payload or {}
    updated_at_str = raw.get('updated_at')
    
    if updated_at_str:
        try:
            # Parse payload date
            payload_dt = parser.parse(updated_at_str)
            if payload_dt.tzinfo:
                payload_dt = payload_dt.astimezone(timezone.utc).replace(tzinfo=None)
            
            # Check if payload date is significantly different from shipped_at
            # e.g. different day
            curr_ship = order.shipped_at
            
            print(f"  Order {order.external_order_id} | Created: {order.order_datetime.date()} | Shipped: {curr_ship.date()} | Payload Updated: {payload_dt.date()} ({updated_at_str})")

            if curr_ship.date() != payload_dt.date():
                print(f"    -> MISMATCH DETECTED")
                to_fix.append((order, payload_dt))
        except Exception as e:
            print(f"  Error parsing {updated_at_str}: {e}")

print(f"\nidentified {len(to_fix)} orders to fix.")

# Apply Fix if confirmed
if len(to_fix) > 0:
    print("Applying fixes...")
    for order, new_dt in to_fix:
        order.shipped_at = new_dt
    
    db.commit()
    print("Fixes applied successfully.")
else:
    print("No fixes needed.")

db.close()
