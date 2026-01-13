
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_invalid_status():
    session = SessionLocal()
    try:
        target_date = datetime(2026, 1, 5)
        next_day = datetime(2026, 1, 6)
        
        print(f"Checking for INVALID statuses on Jan 5 with shipped_at...")
        
        # Valid statuses for an order that has been shipped
        valid_statuses = ['SHIPPED', 'DELIVERED', 'COMPLETED', 'TO_CONFIRM_RECEIVE', 'IN_TRANSIT'] 
        
        invalid_orders = session.query(
            OrderHeader.status_normalized,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day,
            OrderHeader.status_normalized.notin_(valid_statuses)
        ).group_by(OrderHeader.status_normalized).all()
        
        print(f"\nBreakdown of potentially INVALID orders (have shipped_at but status is not shipped):")
        total_invalid = 0
        for status, count in invalid_orders:
            print(f"- {status}: {count}")
            total_invalid += count
            
        print(f"\nTotal Invalid: {total_invalid}")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_invalid_status()
