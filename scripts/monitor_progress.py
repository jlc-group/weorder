import sys
import os
from sqlalchemy import func, text

# Add project root to path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.invoice import InvoiceProfile
from app.models.order import OrderHeader

def check_progress():
    db = SessionLocal()
    try:
        # Total Shopee orders >= 2025
        total_orders = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.channel_code == 'shopee',
            OrderHeader.order_datetime >= '2025-01-01'
        ).scalar()
        
        # Total Invoice Profiles for these orders
        # Using a join or just raw count if we assume all invoices are linked
        # Let's use a join to be accurate
        synced_invoices = db.query(func.count(InvoiceProfile.id)).join(
            OrderHeader, InvoiceProfile.order_id == OrderHeader.id
        ).filter(
            OrderHeader.channel_code == 'shopee',
            OrderHeader.order_datetime >= '2025-01-01'
        ).scalar()
        
        print(f"--- Sync Progress (Shopee 2025) ---")
        print(f"Total Orders: {total_orders}")
        print(f"Synced Invoices: {synced_invoices}")
        if total_orders > 0:
            print(f"Progress: {synced_invoices / total_orders * 100:.2f}%")
            print(f"Remaining: {total_orders - synced_invoices}")
        else:
            print("No orders found for 2025.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_progress()
