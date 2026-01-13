from app.core.database import SessionLocal
from app.models import OrderHeader
import sys
import json
from datetime import datetime

db = SessionLocal()
order_id = "579824638121184088"

print(f"Searching for order: {order_id}")
order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()

if order:
    print(f"Order Found: {order.external_order_id}")
    print(f"Channel: {order.channel_code}")
    print(f"Status Normalized: {order.status_normalized}")
    print(f"Order Date: {order.order_datetime}")
    print(f"Shipped At: {order.shipped_at}")
    
    raw = order.raw_payload
    if raw:
        ct = raw.get("collection_time")
        rt = raw.get("rts_time")
        ut = raw.get("update_time")
        print(f"Raw collection_time: {ct} (Type: {type(ct)})")
        print(f"Raw rts_time: {rt} (Type: {type(rt)})")
        print(f"Raw update_time: {ut} (Type: {type(ut)})")
        
        if ct:
            try:
                # Try direct
                dt1 = datetime.fromtimestamp(ct)
                print(f"fromtimestamp(ct) -> {dt1}")
            except Exception as e:
                print(f"fromtimestamp(ct) Error: {e}")
                
            try:
                # Try / 1000
                dt2 = datetime.fromtimestamp(ct / 1000)
                print(f"fromtimestamp(ct / 1000) -> {dt2}")
            except Exception as e:
                print(f"fromtimestamp(ct / 1000) Error: {e}")
    else:
        print("No raw_payload found.")
            
    print("-" * 30)
else:
    print("Order NOT FOUND in database.")

db.close()
