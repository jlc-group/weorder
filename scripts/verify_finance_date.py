
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.finance import MarketplaceTransaction

def verify_latest_date():
    session = SessionLocal()
    try:
        # Check for Shopee transactions created in the last 5 minutes
        # And print their transaction_date
        # We expect transaction_date to be in 2025, NOT 2026.
        
        print("Checking latest synced Shopee transactions...")
        recent_txs = session.query(MarketplaceTransaction).filter(
            MarketplaceTransaction.platform == 'shopee'
        ).order_by(MarketplaceTransaction.created_at.desc()).limit(5).all()
        
        if not recent_txs:
            print("No new transactions found yet.")
            return

        for tx in recent_txs:
            print(f"ID: {tx.id} | Created: {tx.created_at} | Tx Date: {tx.transaction_date}")
            
    finally:
        session.close()

if __name__ == "__main__":
    verify_latest_date()
