
import sys
import os
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import OrderHeader, StockLedger

db = SessionLocal()
order_id = "53410145-8d51-4bf2-b07d-46501f025f96"

try:
    print(f"Backfilling Order {order_id}...")
    order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
    
    if not order:
        print("Order not found!")
        sys.exit(1)
        
    print(f"Order Found: {order.external_order_id} | Status: {order.status_normalized}")
    print(f"Items: {len(order.items)}")
    
    # Check exists
    exists = db.query(StockLedger).filter(
        StockLedger.reference_id == str(order.id),
        StockLedger.movement_type == 'OUT'
    ).first()
    
    if exists:
        print("StockLedger already exists!")
    else:
        print("Creating entries...")
        for item in order.items:
            print(f" - Adding item: {item.sku} (Qty: {item.quantity})")
            movement = StockLedger(
                warehouse_id=order.warehouse_id,
                product_id=item.product_id,
                movement_type="OUT",
                quantity=item.quantity,
                reference_type="ORDER",
                reference_id=str(order.id),
                note=f"Backfill: {order.external_order_id}",
                created_at=order.order_datetime 
            )
            db.add(movement)
        
        db.commit()
        print("Committed successfully.")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
