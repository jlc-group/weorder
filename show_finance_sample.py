from app.core import get_db
from app.models.finance import MarketplaceTransaction
from sqlalchemy import desc

db = next(get_db())

print("=== Finance Data Sample ===")
count = db.query(MarketplaceTransaction).count()
print(f"Total Records: {count}")

if count > 0:
    samples = db.query(MarketplaceTransaction).order_by(desc(MarketplaceTransaction.id)).limit(5).all()
    for s in samples:
        print("-" * 30)
        print(f"Platform: {s.platform}")
        print(f"Type: {s.transaction_type}")
        print(f"Amount: {s.amount} {s.currency}")
        print(f"Date: {s.transaction_date}")
        print(f"Review: {s.raw_data}") # Show raw payload for user to see details
else:
    print("No records found yet. Sync might still be processing empty periods or catching up.")
