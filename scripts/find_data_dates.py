
import sys
import os
from sqlalchemy import func, cast, Date
sys.path.append(os.getcwd())
from app.core import SessionLocal
from app.models import StockLedger

db = SessionLocal()

# Group by Date
print("Finding dates with Stock Ledger (OUT) data...")
results = db.query(
    cast(StockLedger.created_at, Date).label('date'),
    func.count(StockLedger.id).label('count')
).filter(
    StockLedger.movement_type == 'OUT',
    StockLedger.reference_type == 'ORDER'
).group_by(
    cast(StockLedger.created_at, Date)
).order_by(
    func.count(StockLedger.id).desc()
).all()

print(f"\nFound {len(results)} dates with data:")
for r in results[:10]:
    print(f"Date: {r.date} - Items: {r.count}")

if not results:
    print("No data found yet. Backfill might still be early.")

db.close()
