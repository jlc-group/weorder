
import sys
import os
from datetime import datetime, date
from uuid import uuid4

# Setup Path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader, OrderItem, Product, Warehouse, StockLedger, Company, SalesChannel
from app.services.order_service import OrderService
from app.services.report_service import ReportService
from app.schemas.order import OrderCreate, OrderItemCreate

def verify():
    db = SessionLocal()
    try:
        print("--- Verifying Stock Logic ---")
        
        # 1. Get/Create Dependencies
        company = db.query(Company).first()
        warehouse = db.query(Warehouse).first()
        product = db.query(Product).first()
        
        if not (company and warehouse and product):
            print("Missing dependencies (Company/Warehouse/Product). Run seed first.")
            return

        print(f"Product: {product.sku}")
        print(f"Warehouse: {warehouse.name}")

        # Ensure channel exists
        channel = db.query(SalesChannel).filter(SalesChannel.code == "manual").first()
        if not channel:
            channel = SalesChannel(code="manual", name="Manual Order")
            db.add(channel)
            db.commit()
            print("Created 'manual' channel")

        
        # 2. Create Order
        print("\nCreating Order...")
        order_create = OrderCreate(
            external_order_id=f"TEST-STOCK-{uuid4().hex[:6]}",
            channel_code="manual",
            company_id=company.id,
            warehouse_id=warehouse.id,
            customer_name="Stock Tester",
            customer_phone="0000000000",
            customer_address="Test Address",
            items=[
                OrderItemCreate(
                    product_id=product.id,
                    sku=product.sku,
                    quantity=5,
                    unit_price=100
                )
            ]
        )
        order = OrderService.create_order(db, order_create)
        print(f"Order Created: {order.external_order_id} (Status: {order.status_normalized})")
        
        # 3. Update Status -> SHIPPED (Trigger Stock Logic)
        # Transition: NEW -> PAID -> PACKING -> SHIPPED
        print("\nUpdating Status...")
        OrderService.update_status(db, order.id, "PAID")
        OrderService.update_status(db, order.id, "PACKING")
        success, msg = OrderService.update_status(db, order.id, "SHIPPED")
        print(f"Update to SHIPPED: {success} ({msg})")
        
        # 4. Verify Stock Ledger
        print("\nChecking Stock Ledger...")
        ledger = db.query(StockLedger).filter(
            StockLedger.reference_id == str(order.id),
            StockLedger.movement_type == "OUT",
            StockLedger.reference_type == "ORDER"
        ).first()
        
        if ledger:
            print(f"✅ Stock Ledger Entry Found! Qty: {ledger.quantity}, Type: {ledger.movement_type}")
        else:
            print("❌ Stock Ledger Entry NOT Found!")
            
        # 5. Verify Report
        print("\nChecking Daily Outbound Report...")
        today = date.today()
        report = ReportService.get_daily_outbound_stats(db, today)
        
        # Find our item
        found = False
        for item in report["items"]:
            if item["sku"] == product.sku:
                print(f"Report Item: SKU={item['sku']}, TotalQty={item['total_qty']}")
                if item["total_qty"] >= 5:
                    found = True
        
        if found:
             print("✅ Report includes the item!")
        else:
             print("❌ Report does NOT include the item (or qty mismatch).")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify()
