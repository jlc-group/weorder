import sys
import os
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def inspect_latest_order():
    db = SessionLocal()
    try:
        # Get the most recent TikTok order
        order = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok'
        ).order_by(OrderHeader.order_datetime.desc()).first()

        if order:
            print(f"Order ID: {order.external_order_id}")
            print(f"Status: {order.status_normalized}")
            print("-" * 50)
            if order.raw_payload:
                print(json.dumps(order.raw_payload, indent=2, ensure_ascii=False))
            else:
                print("No raw_payload found!")
        else:
            print("No TikTok orders found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_latest_order()
