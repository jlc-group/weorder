
import sys
import os
from sqlalchemy import func, cast, Date
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_lazada_dist():
    session = SessionLocal()
    try:
        print("Checking Lazada Shipped Date Distribution (Jan 2026)...")
        
        dist = session.query(
            cast(OrderHeader.shipped_at, Date),
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.channel_code == 'lazada',
            OrderHeader.shipped_at >= datetime(2026, 1, 1)
        ).group_by(
            cast(OrderHeader.shipped_at, Date)
        ).order_by(
            cast(OrderHeader.shipped_at, Date)
        ).all()
        
        total_shipped = 0
        for d, count in dist:
            print(f"{d}: {count}")
            total_shipped += count
            
        print(f"Total Lazada Shipped (Jan): {total_shipped}")

    finally:
        session.close()

if __name__ == "__main__":
    check_lazada_dist()
