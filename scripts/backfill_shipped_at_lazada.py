
from app.core.database import SessionLocal
from app.models import OrderHeader
from datetime import datetime
import json

def backfill():
    db = SessionLocal()
    # Find Lazada orders in Jan 2026 with SHIPPED/DELIVERED status and missing shipped_at
    orders = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'lazada',
        OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'COMPLETED']),
        OrderHeader.order_datetime >= '2026-01-01'
    ).all()
    
    count = 0
    for o in orders:
        # Use updated_at from DB or raw_payload
        updated_at = o.updated_at
        if not updated_at and o.raw_payload:
            val = o.raw_payload.get('updated_at')
            if val:
                updated_at = datetime.fromisoformat(val.replace('Z', '+00:00'))
        
        if updated_at and o.shipped_at != updated_at:
            o.shipped_at = updated_at
            count += 1
            
    db.commit()
    print(f"Backfilled {count} Lazada orders with shipped_at timestamps.")
    db.close()

if __name__ == "__main__":
    backfill()
