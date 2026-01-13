
import sys
import os
import requests
from uuid import uuid4
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import InvoiceProfile, OrderHeader

# 1. Create Dummy Profile directly in DB
db = SessionLocal()
order_id = uuid4()
tax_id = "9999999999999"
phone = "0812345678"

# Mock Order Header first (FK constraint)
order = OrderHeader(
    id=order_id,
    external_order_id=f"TEST-{uuid4().hex[:6]}",
    status_normalized="DELIVERED",
    company_id=uuid4(),
    # Other required fields...
)
# Actually, let's just use an EXISTING valid order to avoid constraint hell
existing_order = db.query(OrderHeader).first()
if not existing_order:
    print("No orders found to attach profile to. Cannot test.")
    sys.exit(1)

# Check if profile exists for this order
existing_profile = db.query(InvoiceProfile).filter(InvoiceProfile.order_id == existing_order.id).first()
if existing_profile:
    print(f"Using existing profile for test: {existing_profile.tax_id} / {existing_profile.phone}")
    tax_id = existing_profile.tax_id
    phone = existing_profile.phone
else:
    print(f"Creating Dummy Profile using Order {existing_order.id}")
    profile = InvoiceProfile(
        order_id=existing_order.id,
        profile_type="PERSONAL",
        invoice_name="Test User Autofill",
        tax_id=tax_id,
        branch="00000",
        address_line1="123 Test Road",
        phone=phone,
        email="test@example.com",
        status="PENDING"
    )
    db.add(profile)
    db.commit()

db.close()

# 2. Test API Lookup using requests (assuming server running at localhost:9202)
import time
time.sleep(1) 

print(f"\n--- Testing Lookup API ---")
try:
    # Test Tax ID
    resp = requests.get(f"http://localhost:9202/api/invoice-request/lookup?tax_id={tax_id}")
    print(f"Lookup by Tax ID ({tax_id}): {resp.status_code}")
    print(resp.json())
    
    # Test Phone
    resp = requests.get(f"http://localhost:9202/api/invoice-request/lookup?phone={phone}")
    print(f"Lookup by Phone ({phone}): {resp.status_code}")
    print(resp.json())

except Exception as e:
    print(f"API Test Failed: {e}")
