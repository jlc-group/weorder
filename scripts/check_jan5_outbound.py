
import sys
import os
from sqlalchemy import func
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_jan5_outbound():
    session = SessionLocal()
    try:
        target_date = datetime(2026, 1, 5)
        next_day = target_date + timedelta(days=1)
        
        print(f"Checking Outbound for {target_date.date()}...")
        
        # Total
        total = session.query(OrderHeader).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).count()
        
        print(f"Total Shipped: {total:,}")
        
        # Breakdown
        breakdown = session.query(
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).group_by(OrderHeader.channel_code).all()
        
        for ch, count in breakdown:
            print(f"- {ch}: {count:,}")

    finally:
        session.close()

if __name__ == "__main__":
    check_jan5_outbound()
