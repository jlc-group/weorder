
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_tiktok_raw_status():
    session = SessionLocal()
    try:
        target_date = datetime(2026, 1, 5)
        next_day = datetime(2026, 1, 6)
        
        print(f"Checking TikTok Raw Statuses for orders 'shipped' on Jan 5...")
        
        # Breakdown by Raw Status
        raw_counts = session.query(
            OrderHeader.status_raw,
            OrderHeader.status_normalized,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day,
            OrderHeader.channel_code == 'tiktok'
        ).group_by(
            OrderHeader.status_raw,
            OrderHeader.status_normalized
        ).all()
        
        for raw, norm, count in raw_counts:
            print(f"Raw: {raw:<20} | Norm: {norm:<15} | Count: {count}")

    finally:
        session.close()

if __name__ == "__main__":
    check_tiktok_raw_status()
