#!/usr/bin/env python3
"""
Inspect Lazada and TikTok Ghost Payloads.
Find the correct field for historical shipping time.
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

def inspect_platform(platform, date_str):
    print(f"\n=== Inspecting {platform} Ghosts on {date_str} ===")
    orders = db.query(OrderHeader).filter(
        OrderHeader.channel_code == platform,
        cast(OrderHeader.shipped_at, Date) == date_str,
        OrderHeader.order_datetime < '2026-01-01'
    ).limit(3).all()
    
    for order in orders:
        print(f"ID: {order.external_order_id}")
        raw = order.raw_payload or {}
        print(f"  Keys: {list(raw.keys())}")
        
        if platform == 'lazada':
            print(f"  updated_at: {raw.get('updated_at')}")
            # Lazada often has 'statuses' list or similar in detailed payload, 
            # but let's see what's in the shallow payload we have.
            print(f"  status: {raw.get('status')}")
            
        elif platform == 'tiktok':
            print(f"  update_time: {raw.get('update_time')}")
            print(f"  rts_time: {raw.get('rts_time')}")
            print(f"  delivery_time: {raw.get('delivery_time')}")
            # TikTok might have ms timestamp
            
        print("-" * 30)

inspect_platform('lazada', '2026-01-07')
inspect_platform('tiktok', '2026-01-05')

db.close()
