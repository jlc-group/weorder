
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def diagnose_missing_shipped_at():
    session = SessionLocal()
    try:
        # User is looking at Jan 5. So we look at orders created Jan 1-5.
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 1, 8)
        
        print(f"Checking Shopee/Lazada orders created between {start_date.date()} and {end_date.date()}...")
        print("Conditions: Status is Shipped/Delivered/Completed, but 'shipped_at' is NULL.")
        
        missing = session.query(
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date,
            OrderHeader.channel_code.in_(['shopee', 'lazada']),
            OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'COMPLETED']),
            OrderHeader.shipped_at.is_(None)
        ).group_by(OrderHeader.channel_code).all()
        
        if not missing:
            print("No missing timestamps found for this period.")
        else:
            print("\nFOUND MISSING 'shipped_at' records:")
            for ch, count in missing:
                print(f"- {ch}: {count} orders")
                
        # Also check if they HAVE a timestamp but it's on a different day?
        # Maybe they shipped on Jan 6 but user expects Jan 5?
        
        print("\nDistribution of 'shipped_at' for Shopee/Lazada orders created in Jan 1-5:")
        dist = session.query(
            func.date(OrderHeader.shipped_at),
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date,
            OrderHeader.channel_code.in_(['shopee', 'lazada']),
            OrderHeader.shipped_at.isnot(None)
        ).group_by(
            func.date(OrderHeader.shipped_at),
            OrderHeader.channel_code
        ).order_by(func.date(OrderHeader.shipped_at)).all()
        
        for d, ch, c in dist:
            print(f"- Shipped {d} | {ch}: {c}")

    finally:
        session.close()

if __name__ == "__main__":
    diagnose_missing_shipped_at()
