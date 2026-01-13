
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.finance import MarketplaceTransaction

def check_raw_data():
    session = SessionLocal()
    try:
        tx = session.query(MarketplaceTransaction).filter(MarketplaceTransaction.platform == 'shopee').first()
        if tx:
            print("=== Sample Transaction Raw Data ===")
            print(f"Transaction Date in DB: {tx.transaction_date}")
            print("Raw Data Keys:", tx.raw_data.keys() if isinstance(tx.raw_data, dict) else "Not a dict")
            print("Full Raw Data:")
            print(json.dumps(tx.raw_data, indent=2, default=str))
        else:
            print("No Shopee transactions found.")
    finally:
        session.close()

if __name__ == "__main__":
    check_raw_data()
