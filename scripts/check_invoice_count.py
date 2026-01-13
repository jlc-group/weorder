
import sys
import os

# Add project root to python path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.invoice import InvoiceProfile
from sqlalchemy import desc

def check_data():
    db = SessionLocal()
    try:
        count = db.query(InvoiceProfile).count()
        print(f"Total Invoice Profiles: {count}")
        
        last_invoice = db.query(InvoiceProfile).order_by(desc(InvoiceProfile.created_at)).first()
        if last_invoice:
            print("\nLatest Invoice Profile:")
            print(f"ID: {last_invoice.id}")
            print(f"Order ID: {last_invoice.order_id}")
            print(f"Invoice Name: {last_invoice.invoice_name}")
            print(f"Tax ID: {last_invoice.tax_id}")
            print(f"Address: {last_invoice.address_line1} {last_invoice.address_line2} {last_invoice.subdistrict} {last_invoice.district} {last_invoice.province} {last_invoice.postal_code}")
            print(f"Source: {last_invoice.created_source}")
            print(f"Platform Data (Sample): {str(last_invoice.platform_invoice_data)[:100]}...")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
