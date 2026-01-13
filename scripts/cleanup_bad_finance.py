
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.finance import MarketplaceTransaction

def cleanup_finance():
    session = SessionLocal()
    try:
        # Delete based on erroneous transaction_date (Jan 2026)
        cutoff_date = datetime(2026, 1, 1)
        
        print(f"Deleting Shopee transactions with date >= {cutoff_date}...")
        
        q = session.query(MarketplaceTransaction).filter(
            MarketplaceTransaction.platform == 'shopee',
            MarketplaceTransaction.transaction_date >= cutoff_date
        )
        
        count = q.count()
        print(f"Found {count} records to delete.")
        
        if count > 0:
            q.delete(synchronize_session=False)
            session.commit()
            print("Deletion complete.")
        else:
            print("Nothing to delete.")
            
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_finance()
