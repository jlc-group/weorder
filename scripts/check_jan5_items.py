
import sys
import os
from sqlalchemy import func

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader, OrderItem

def check_jan5_items():
    session = SessionLocal()
    try:
        from datetime import datetime
        target_date = datetime(2026, 1, 5)
        next_day = datetime(2026, 1, 6)
        
        print(f"Checking Outbound ITEMS (Quantity) for {target_date.date()}...")
        
        # Join OrderHeader -> OrderItem
        # Sum quantity
        total_items = session.query(func.sum(OrderItem.quantity)).join(OrderHeader).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).scalar()
        
        print(f"Total Items Shipped: {total_items}")
        
        # Breakdown by Platform
        breakdown = session.query(
            OrderHeader.channel_code,
            func.sum(OrderItem.quantity)
        ).join(OrderHeader).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).group_by(OrderHeader.channel_code).all()
        
        for ch, count in breakdown:
            print(f"- {ch}: {count}")

    finally:
        session.close()

if __name__ == "__main__":
    check_jan5_items()
