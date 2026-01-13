
import sys
import os
import random
from datetime import datetime, timedelta
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import StockLedger, OrderHeader, Warehouse, Product

db = SessionLocal()

# 1. Get Default Warehouse
wh = db.query(Warehouse).first()
if not wh:
    print("No warehouse found. Cannot seed.")
    sys.exit(1)

# 2. Get some SHIPPED orders from 2025
orders = db.query(OrderHeader).filter(
    OrderHeader.status_normalized == 'SHIPPED',
    OrderHeader.order_datetime >= '2025-12-01'
).limit(50).all()

print(f"Found {len(orders)} orders to seed.")

count = 0
for order in orders:
    # Check if exists
    exists = db.query(StockLedger).filter(
        StockLedger.reference_id == str(order.id),
        StockLedger.reference_type == 'ORDER'
    ).first()
    if exists: 
        print(f"Order {order.id} skipped: Already exists in Ledger.")
        continue

    if not order.items: 
        print(f"Order {order.id} skipped: No Items.")
        continue

    for item in order.items:
        product_id = item.product_id
        if not product_id:
            # Try find by sku
            p = db.query(Product).filter(Product.sku == item.sku).first()
            if p: 
                product_id = p.id
            else:
                # FALLBACK FOR DEMO: Use any product
                fallback = db.query(Product).first()
                if fallback:
                    print(f"Item {item.sku}: using fallback product {fallback.sku}")
                    product_id = fallback.id

        if not product_id: 
            print(f"Item {item.sku} skipped: No Product ID (and no fallback).")
            continue

        ledger = StockLedger(
            warehouse_id=wh.id,
            product_id=product_id,
            movement_type='OUT',
            quantity=item.quantity,
            reference_type='ORDER',
            reference_id=str(order.id),
            created_at=order.order_datetime or datetime.now(),
            created_by='SEED_DEMO'
        )
        db.add(ledger)
        count += 1

db.commit()
print(f"Seeded {count} ledger entries.")
db.close()
