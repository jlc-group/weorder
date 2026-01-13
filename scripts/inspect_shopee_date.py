
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.finance import MarketplaceTransaction

def recursive_find_time(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            new_path = f"{path}.{k}" if path else k
            if "time" in k.lower() or "date" in k.lower():
                print(f"Found key: {new_path} = {v}")
            if isinstance(v, (dict, list)):
                recursive_find_time(v, new_path)
    elif isinstance(d, list):
        for i, item in enumerate(d):
            new_path = f"{path}[{i}]"
            recursive_find_time(item, new_path)

def inspect_date():
    session = SessionLocal()
    try:
        # Get a sample transaction
        tx = session.query(MarketplaceTransaction).filter(MarketplaceTransaction.platform == 'shopee').first()
        if tx:
            print(f"=== Inspecting Transaction {tx.id} ===")
            print(f"Current Transaction Date: {tx.transaction_date}")
            if tx.raw_data:
                recursive_find_time(tx.raw_data)
            else:
                print("No raw_data found.")
        else:
            print("No transactions found.")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_date()
