
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_order_volume():
    session = SessionLocal()
    try:
        # Count Shopee Orders in 2025
        count_2025 = session.query(OrderHeader).filter(
            OrderHeader.channel_code == 'shopee',
            OrderHeader.order_datetime >= datetime(2025, 1, 1),
            OrderHeader.order_datetime < datetime(2026, 1, 1)
        ).count()
        
        print(f"Total Shopee Orders in 2025: {count_2025:,}")
        print("-" * 30)
        print("Estimated Financial Transactions:")
        print(f"If avg 5 tx per order (Price, Fee, Comm, Ship, Service): {count_2025 * 5:,}")
        print(f"If avg 7 tx per order ( + Voucher, Rebate, etc.): {count_2025 * 7:,}")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_order_volume()
