#!/usr/bin/env python3
"""
Check pickup_done_time values.
"""
import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import cast, Date

db = SessionLocal()

print("=== Checking pickup_done_time for Shopee Jan 8 Artifacts ===")
target_date = '2026-01-08'

orders = db.query(OrderHeader).filter(
    OrderHeader.channel_code == 'shopee',
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.order_datetime < '2026-01-01'
).limit(5).all()

for order in orders:
    raw = order.raw_payload
    print(f"ID: {order.external_order_id}")
    print(f"  Created: {order.order_datetime}")
    
    pickup = raw.get('pickup_done_time')
    update = raw.get('update_time')
    
    print(f"  Raw pickup_done_time: {pickup}")
    if pickup:
        print(f"  -> Converted: {datetime.fromtimestamp(pickup)}")
        
    print(f"  Raw update_time: {update}")
    if update:
        print(f"  -> Converted: {datetime.fromtimestamp(update)}")
    
    print("-" * 30)

db.close()
