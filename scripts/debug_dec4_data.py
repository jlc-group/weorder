
import sys
import os
from datetime import datetime
from uuid import UUID

sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader, StockLedger

def check_date():
    db = SessionLocal()
    try:
        # Check Orders on Dec 4
        print("Checking Dec 4 2025...")
        start_date = "2025-12-04 00:00:00"
        end_date = "2025-12-04 23:59:59"
        
        orders = db.query(OrderHeader).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime <= end_date
        ).all()
        
        print(f"Total Orders on Dec 4: {len(orders)}")
        
        if orders:
            sample = orders[0]
            print(f"Sample Order: {sample.external_order_id} Status: {sample.status_normalized}")
            print(f"Order Date: {sample.order_datetime}")
            print(f"Updated At: {sample.updated_at}")
            
            # Check Stock Ledger for this order
            ledgers = db.query(StockLedger).filter(
                StockLedger.reference_id == str(sample.id),
                StockLedger.reference_type == "ORDER"
            ).all()
            
            print(f"Stock Ledger Entries for this order: {len(ledgers)}")
            for l in ledgers:
                print(f" - Type: {l.movement_type}, Date: {l.created_at}")

        # Check Stock Ledger entries created on Dec 4 specifically
        print("\nChecking StockLedger created on Dec 4...")
        ledger_entries = db.query(StockLedger).filter(
             StockLedger.created_at >= start_date,
             StockLedger.created_at <= end_date,
             StockLedger.movement_type == "OUT"
        ).count()
        print(f"Total OUT movements dated Dec 4: {ledger_entries}")

    finally:
        db.close()

if __name__ == "__main__":
    check_date()
