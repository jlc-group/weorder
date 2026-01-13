
import sys
import os
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import OrderHeader, StockLedger

target_statuses = ["SHIPPED", "COMPLETED", "DELIVERED", "READY_TO_SHIP"]

db = SessionLocal()
print(f"Counting Orders with statuses: {target_statuses}")

count = db.query(OrderHeader).filter(OrderHeader.status_normalized.in_(target_statuses)).count()
print(f"Total Candidate Orders: {count}")

# Check intersection with Ledger
# This might be slow but let's check a sample
if count > 0:
    sample = db.query(OrderHeader).filter(OrderHeader.status_normalized.in_(target_statuses)).first()
    print(f"Sample Candidate: {sample.id} | {sample.status_normalized}")
    
    exists = db.query(StockLedger).filter(
        StockLedger.reference_id == str(sample.id),
        StockLedger.reference_type == "ORDER",
        StockLedger.movement_type == "OUT"
    ).first()
    print(f"Has Ledger Entry? {exists is not None}")

# Check Dec 4 specifics
print("\n--- Dec 4 Check ---")
start = "2025-12-04 00:00:00"
end = "2025-12-04 23:59:59"
dec4_candidates = db.query(OrderHeader).filter(
    OrderHeader.order_datetime >= start,
    OrderHeader.order_datetime <= end,
    OrderHeader.status_normalized.in_(target_statuses)
).count()
print(f"Dec 4 Candidates: {dec4_candidates}")

dec4_total = db.query(OrderHeader).filter(
    OrderHeader.order_datetime >= start,
    OrderHeader.order_datetime <= end
).count()
print(f"Dec 4 Total Orders (All Status): {dec4_total}")
