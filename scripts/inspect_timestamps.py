from app.core.database import SessionLocal
from app.models import OrderHeader
import json
from datetime import datetime

db = SessionLocal()

target_id = "581693998548878727"
order = db.query(OrderHeader).filter(OrderHeader.external_order_id == target_id).first()

if order and order.raw_payload:
    payload = order.raw_payload if isinstance(order.raw_payload, dict) else json.loads(order.raw_payload)
    
    print("-" * 30)
    print(f"External ID: {target_id}")
    
    for key in ['create_time', 'update_time', 'rts_time', 'collection_time', 'shipping_due_time']:
        ts = payload.get(key)
        if ts:
            # TikTok ts are usually seconds
            dt_object = datetime.fromtimestamp(ts)
            print(f"{key}: {ts} -> {dt_object}")
        else:
            print(f"{key}: None")

db.close()
