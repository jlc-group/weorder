from app.core.database import SessionLocal
from app.models import OrderHeader
import json

db = SessionLocal()

target_id = "581693998548878727"
order = db.query(OrderHeader).filter(OrderHeader.external_order_id == target_id).first()

if order:
    print(f"External ID: {order.external_order_id}")
    print(f"Status Normalized: {order.status_normalized}")
    print(f"Status Raw: {order.status_raw}")
    print(f"Shipped At: {order.shipped_at}")
    print(f"Order Updated At (Platform): {order.updated_at}")
    
    # Try to print relevant parts of raw_payload if available
    if order.raw_payload:
        try:
            # It's likely a dict already if sqlalchemy handles JSON, or string
            payload = order.raw_payload if isinstance(order.raw_payload, dict) else json.loads(order.raw_payload)
            print("Raw Payload Keys:", payload.keys())
            print("Create Time:", payload.get('create_time'))
            print("Update Time:", payload.get('update_time'))
            
            # Check for shipping info in payload
            # TikTok often puts it in 'package_list' or similar? Or just top level.
            # Based on previous file reads, let's see what's there.
        except Exception as e:
            print(f"Error parsing payload: {e}")
else:
    print("Order not found")

db.close()
