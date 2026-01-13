
import sys
import os
from sqlalchemy import func
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def diagnose_jan5():
    session = SessionLocal()
    try:
        target_date = datetime(2026, 1, 5)
        next_day = target_date + timedelta(days=1)
        
        print(f"=== DIAGNOSTIC: Jan 5, 2026 ({target_date.date()}) ===")
        
        # 1. Breakdown by Status (Ensuring we aren't counting Cancelled)
        print("\n1. Breakdown by Status Normalized:")
        status_counts = session.query(
            OrderHeader.status_normalized,
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).group_by(
            OrderHeader.status_normalized,
            OrderHeader.channel_code
        ).all()
        
        for status, ch, count in status_counts:
            print(f"   [{ch.upper()}] {status}: {count}")

        # 2. Hourly Distribution (Check for Timezone Shift)
        print("\n2. Hourly Distribution (UTC):")
        hourly = session.query(
            func.extract('hour', OrderHeader.shipped_at).label('h'),
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).group_by('h').order_by('h').all()
        
        for h, count in hourly:
            print(f"   Hour {int(h):02d}: {count}")

        # 3. Check specific large batch (TikTok)
        # Verify if Shipped At is exactly the same for many orders (Batch update artifact?)
        print("\n3. Distinct Shipped Times (Top 5 most frequent timestamps):")
        top_times = session.query(
            OrderHeader.shipped_at,
            func.count(OrderHeader.id).label('cnt')
        ).filter(
            OrderHeader.shipped_at >= target_date,
            OrderHeader.shipped_at < next_day
        ).group_by(OrderHeader.shipped_at).order_by(func.count(OrderHeader.id).desc()).limit(5).all()
        
        for ts, cnt in top_times:
            print(f"   {ts}: {cnt} orders")

    finally:
        session.close()

if __name__ == "__main__":
    diagnose_jan5()
