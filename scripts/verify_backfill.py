from app.core.database import SessionLocal
from app.models import OrderHeader

db = SessionLocal()

# The order we checked earlier: 581693998548878727
# It had shipped_at = 2026-01-02 ...
# Correct collection_time was 2025-12-18 ... (wait, the year was 2025 in the timestamp print?)
# Let's re-verify the value.

target_id = "581693998548878727"
order = db.query(OrderHeader).filter(OrderHeader.external_order_id == target_id).first()

if order:
    print(f"Order: {target_id}")
    print(f"Current Shipped At: {order.shipped_at}")
    print(f"Current Updated At: {order.updated_at}")
else:
    print("Order not found")

db.close()
