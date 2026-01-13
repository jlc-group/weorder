#!/usr/bin/env python3
"""
Bulk Cleanup Script:
Marks stale 'NEW' orders (older than 60 days) as 'CANCELLED'.
This cleans up the "Pending Review" backlog on the dashboard.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import text
from datetime import datetime, timedelta

db = SessionLocal()

# Threshold: 60 days ago
cutoff_date = datetime.utcnow() - timedelta(days=60)

print(f"=== Cleaning Stale Orders (Older than {cutoff_date.date()}) ===")

# 1. Count targets
count_query = db.query(OrderHeader).filter(
    OrderHeader.status_normalized == 'NEW',
    OrderHeader.order_datetime < cutoff_date
)
target_count = count_query.count()

print(f"Found {target_count:,} stale 'NEW' orders.")

if target_count > 0:
    # 2. Execute Update
    # Using raw SQL for speed and ensuring updated_at changes
    # We set status to CANCELLED and note the reason in raw_payload or status_raw
    
    update_stmt = text("""
        UPDATE order_header
        SET status_normalized = 'CANCELLED',
            status_raw = 'AUTO_CLEANUP',
            updated_at = NOW()
        WHERE status_normalized = 'NEW'
          AND order_datetime < :cutoff
    """)
    
    result = db.execute(update_stmt, {"cutoff": cutoff_date})
    db.commit()
    
    print(f"✅ Successfully updated {result.rowcount:,} orders to CANCELLED.")
else:
    print("No stale orders found to clean.")

db.close()
