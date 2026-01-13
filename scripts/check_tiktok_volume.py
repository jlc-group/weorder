
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_tiktok_volume():
    session = SessionLocal()
    try:
        # Count TikTok Orders in 2025
        count_2025 = session.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.order_datetime >= datetime(2025, 1, 1),
            OrderHeader.order_datetime < datetime(2026, 1, 1)
        ).count()
        
        print(f"Total TikTok Orders in 2025: {count_2025:,}")
        print("-" * 30)
        print("Estimated Financial Transactions (TikTok structure might be simpler or complex):")
        # TikTok often groups Settle in statements, but line items still exist.
        print(f"If avg 4 tx per order: {count_2025 * 4:,}") 
        print(f"If avg 6 tx per order: {count_2025 * 6:,}")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_tiktok_volume()
