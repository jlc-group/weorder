
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader

def get_summary():
    db = SessionLocal()
    try:
        start_date = datetime(2025, 1, 1)
        # Using a far future date to include everything up to Jan 2026 and beyond if needed, 
        # or strictly to end of Jan 2026. User said "Jan 2025 - Jan 2026".
        # Let's cover until now/future to be safe, or specifically end of Jan 2026.
        end_date = datetime(2026, 2, 1) 

        results = db.query(
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date
        ).group_by(OrderHeader.channel_code).all()

        print("\n| Platform | Order Count |")
        print("|---|---|")
        total = 0
        for channel, count in results:
            channel_name = channel.capitalize() if channel else "Unknown"
            print(f"| {channel_name} | {count:,} |")
            total += count
        print(f"| **Total** | **{total:,}** |")

    finally:
        db.close()

if __name__ == "__main__":
    get_summary()
