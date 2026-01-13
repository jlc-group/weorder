
import sys
import os
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import StockLedger, OrderHeader

db = SessionLocal()

total_orders = db.query(OrderHeader).count()
total_ledger = db.query(StockLedger).count()
out_ledger = db.query(StockLedger).filter(StockLedger.movement_type == 'OUT').count()

print(f"Total Orders: {total_orders}")
print(f"Total Ledger Entries: {total_ledger}")
print(f"Total OUT Ledger Entries: {out_ledger}")

# Check 5 recent ledger entries
recents = db.query(StockLedger).order_by(StockLedger.created_at.desc()).limit(5).all()
print("\nRecent Ledger Entries:")
for r in recents:
    print(f"ID: {r.id} | Ref: {r.reference_id} | Created: {r.created_at} | Type: {r.movement_type}")

db.close()
