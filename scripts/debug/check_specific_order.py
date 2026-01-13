import sys
import os
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_order(order_id):
    db = SessionLocal()
    try:
        order = db.query(OrderHeader).filter(
            OrderHeader.external_order_id == order_id
        ).first()

        if order:
            print(f"Order ID: {order.external_order_id}")
            print(f"Payment Method: {order.payment_method}")
            print(f"Payment Status: {order.payment_status}")
            print(f"Status: {order.status_normalized}")
            print("-" * 50)
            if order.raw_payload:
                raw_payment = order.raw_payload.get("payment_method_name")
                print(f"Raw 'payment_method_name': {raw_payment}")
            else:
                print("No raw_payload found!")
        else:
            print(f"Order {order_id} not found in database.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_order("581911040263816211")
