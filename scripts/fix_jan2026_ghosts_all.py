#!/usr/bin/env python3
"""
Comprehensive Fix for Jan 2026 Ghosts (Lazada & Shopee).
- Shopee: Uses `pickup_done_time` or `update_time`.
- Lazada: Uses `updated_at` (since payload confirms it holds historical date).
- TikTok: SKIPPED (Analysis shows they are legitimate Jan 2026 activities).

Target: Orders 'Shipped' in Jan 2026 but Created < Jan 1, 2026.
"""
import sys
import os
import time
from datetime import datetime, timezone
from dateutil import parser # for lenient parsing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import cast, Date

db = SessionLocal()

print("=== Executing Comprehensive Fix for Jan 2026 ===")
START_DATE = '2026-01-01'
END_DATE = '2026-01-31'

def fix_shopee():
    print("\n--- Fixing Shopee ---")
    query = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'shopee',
        cast(OrderHeader.shipped_at, Date) >= START_DATE,
        cast(OrderHeader.shipped_at, Date) <= END_DATE,
        OrderHeader.order_datetime < START_DATE
    )
    
    total = query.count()
    print(f"Found {total:,} Shopee ghosts.")
    
    if total == 0:
        return

    updated_count = 0
    skipped_count = 0
    
    # Process in batches
    offset = 0
    batch_size = 1000
    
    while True:
        # Re-query to avoid stale objects, but use offset/limit or just iterate
        # Iterating directly is risky if we modify the sort key, but here we modify shipped_at
        # which is part of filter... so the set changes.
        # Safer to fetch one batch, process, commit.
        
        batch = query.limit(batch_size).all()
        if not batch:
            break
            
        for order in batch:
            raw = order.raw_payload or {}
            ts = raw.get('pickup_done_time') or raw.get('update_time')
            
            if ts:
                try:
                    new_dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                    order.shipped_at = new_dt
                    updated_count += 1
                except Exception as e:
                    print(f"Error parsing Shopee ts {ts}: {e}")
                    skipped_count += 1
            else:
                skipped_count += 1
        
        db.commit()
        print(f"  Processed batch... Total Updated so far: {updated_count}")
        # Since we modified 'shipped_at', these records will naturally fall out of the query scope
        # if their new date is not in Jan 2026 (likely 2025).
        # So we can just loop 'limit' again without offset? 
        # CAREFUL: If the new date IS in Jan 2026 (legit backlog), they will stay in query filter.
        # This would cause infinite loop.
        # BETTER: Fetch ALL IDs first, then iterate IDs.
        break # Safety break for this pattern, let's switch to ID-based approach below.

def fix_shopee_safe():
    print("\n--- Fixing Shopee (Safe Mode) ---")
    # Fetch IDs first
    ids = [o.id for o in db.query(OrderHeader.id).filter(
        OrderHeader.channel_code == 'shopee',
        cast(OrderHeader.shipped_at, Date) >= START_DATE,
        cast(OrderHeader.shipped_at, Date) <= END_DATE,
        OrderHeader.order_datetime < START_DATE
    ).all()]
    
    print(f"Found {len(ids):,} Shopee ghosts to process.")
    
    updated_count = 0
    for i, oid in enumerate(ids):
        order = db.query(OrderHeader).get(oid)
        if not order: continue
        
        raw = order.raw_payload or {}
        ts = raw.get('pickup_done_time') or raw.get('update_time')
        
        if ts:
            try:
                # Assuming raw timestamp is epoch
                new_dt = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                order.shipped_at = new_dt
                updated_count += 1
            except:
                pass
        
        if i % 500 == 0:
            db.commit()
            print(f"  Progress: {i}/{len(ids)}")
            
    db.commit()
    print(f"Shopee Fix Complete. Updated: {updated_count}")

def fix_lazada_safe():
    print("\n--- Fixing Lazada (Safe Mode) ---")
    # Fetch IDs first
    ids = [o.id for o in db.query(OrderHeader.id).filter(
        OrderHeader.channel_code == 'lazada',
        cast(OrderHeader.shipped_at, Date) >= START_DATE,
        cast(OrderHeader.shipped_at, Date) <= END_DATE,
        OrderHeader.order_datetime < START_DATE
    ).all()]
    
    print(f"Found {len(ids):,} Lazada ghosts to process.")
    
    updated_count = 0
    for i, oid in enumerate(ids):
        order = db.query(OrderHeader).get(oid)
        if not order: continue
        
        raw = order.raw_payload or {}
        # Lazada format: "2025-12-14 12:17:34 +0700"
        date_str = raw.get('updated_at')
        
        if date_str:
            try:
                new_dt = parser.parse(date_str)
                # Convert to naive UTC if needed, or naive local depending on DB convention
                # Our DB seems to use naive timestamps (judging by previous scripts)
                # But 'parser' returns aware if offset is present.
                # Let's align with the existing system (naive)
                if new_dt.tzinfo:
                    new_dt = new_dt.astimezone(timezone.utc).replace(tzinfo=None)
                
                order.shipped_at = new_dt
                updated_count += 1
            except Exception as e:
                # print(f"Error parsing Lazada date {date_str}: {e}")
                pass
        
        if i % 100 == 0:
            db.commit()
            print(f"  Progress: {i}/{len(ids)}")
            
    db.commit()
    print(f"Lazada Fix Complete. Updated: {updated_count}")

try:
    fix_shopee_safe()
    fix_lazada_safe()
finally:
    db.close()
