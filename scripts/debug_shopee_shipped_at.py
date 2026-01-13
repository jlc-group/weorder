#!/usr/bin/env python3
"""
Investigate why 30k Shopee orders have shipped_at on Jan 8, 2026.
Check their creation date and raw payload to see real shipping time.
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.order import OrderHeader
from sqlalchemy import cast, Date, desc

db = SessionLocal()

print("=== Investigating Shopee Orders Shipped on Jan 8 ===")
target_date = '2026-01-08'

# Get a sample of Shopee orders shipped on Jan 8 but created in 2025
shopee_orders = db.query(OrderHeader).filter(
    OrderHeader.channel_code == 'shopee',
    cast(OrderHeader.shipped_at, Date) == target_date,
    OrderHeader.order_datetime < '2026-01-01'
).limit(5).all()

print(f"Found {len(shopee_orders)} sample orders created in 2025 but 'shipped' on Jan 8, 2026:\n")

for order in shopee_orders:
    print(f"ID: {order.external_order_id}")
    print(f"  Created: {order.order_datetime}")
    print(f"  Shipped (DB): {order.shipped_at}")
    
    # Check raw payload for clues
    raw = order.raw_payload
    if raw:
        print(f"  Raw Status: {raw.get('order_status')}")
        print(f"  Raw Create Time: {raw.get('create_time')}")
        # Shopee specific fields for shipping time?
        # Usually 'shipping_confirm_time' or similar?
        print(f"  Raw Payload Keys: {list(raw.keys())}")
        if 'shipping_carrier' in raw:
             print(f"  Carrier: {raw.get('shipping_carrier')}")
    print("-" * 30)

db.close()
