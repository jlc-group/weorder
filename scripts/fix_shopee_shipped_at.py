#!/usr/bin/env python3
"""
Fix Shopee Shipped At:
Updates `shipped_at` for 30k Shopee orders erroneously marked as shipped on Jan 8, 2026.
Uses `pickup_done_time` (or `update_time`) from `raw_payload` to restore historical accuracy.
"""
import sys
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import cast, Date

db = SessionLocal()

print("=== Fixing Shopee Shipped Dates (Restoring History) ===")
# Target the specific artifact date
target_date = '2026-01-08'

# Query the affected batch: Shopee orders "shipped" on Jan 8 but created before 2026
query = db.query(OrderHeader).filter(
    OrderHeader.channel_code == 'shopee',
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.order_datetime < '2026-01-01'
)

total_count = query.count()
print(f"Found {total_count:,} orders to fix.")

processed = 0
updated = 0
skipped = 0

# Limit batch size to prevent memory issues, but loop until done
batch_size = 1000
has_more = True

while has_more:
    orders = query.limit(batch_size).all()
    if not orders:
        has_more = False
        break
        
    for order in orders:
        processed += 1
        raw = order.raw_payload or {}
        
        # Priority 1: pickup_done_time
        ts = raw.get('pickup_done_time')
        
        # Priority 2: update_time (fallback)
        if not ts:
            ts = raw.get('update_time')
            
        if ts:
            # Convert timestamp to naive datetime (stored as UTC in DB usually, but let's check model)
            # The model fields are generally offset-naive in some setups, but let's be careful.
            # SQLAlchemy DateTime usually takes Python datetime objects.
            
            # Timestamp is unix epoch
            new_dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None) # naive UTC
            
            # Only update if meaningful change (diff > 1 day)
            # comparing naive to naive (if order.shipped_at is naive) or aware to aware
            # order.shipped_at in session might be aware or naive depending on driver.
            # Let's just set it.
            
            order.shipped_at = new_dt
            updated += 1
        else:
            skipped += 1
            
    db.commit()
    print(f"Processed {processed}/{total_count} (Updated: {updated})...")
    
    # Refresh query count to see if we are done (since we modified the target set?)
    # Wait, we are modifying 'shipped_at', so they will no longer match 'shipped_at == Jan 8'
    # SO the query will naturally return different items next batch.
    
    # Small pause to be nice to DB
    time.sleep(0.1)

print(f"=== Complete ===")
print(f"Total Processed: {processed}")
print(f"Total Updated: {updated}")
print(f"Total Skipped (No timestamp found): {skipped}")

db.close()
