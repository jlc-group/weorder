
import sys
import os
from sqlalchemy import func, case
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def verify_outbound():
    session = SessionLocal()
    try:
        print("=== Outbound / Order Count Verification ===")
        
        # 1. Check for Shipped Orders without shipped_at
        missing_date = session.query(func.count(OrderHeader.id)).filter(
            OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'COMPLETED']), # Assuming COMPLETED also implies shipped? Or just SHIPPED/DELIVERED
            OrderHeader.shipped_at.is_(None)
        ).scalar()
        
        print(f"Orders status SHIPPED/DELIVERED but MISSING 'shipped_at': {missing_date}")
        
        # 2. Check Daily Outbound Stats (shipped_at) for Jan 2026
        print("\n--- Daily Outbound (shipped_at) Jan 2026 ---")
        daily_stats = session.query(
            func.date(OrderHeader.shipped_at).label('ship_date'),
            func.count(OrderHeader.id).label('count')
        ).filter(
            OrderHeader.shipped_at >= datetime(2026, 1, 1),
            OrderHeader.shipped_at < datetime(2026, 2, 1)
        ).group_by(
            func.date(OrderHeader.shipped_at)
        ).order_by(
            func.date(OrderHeader.shipped_at)
        ).all()
        
        for day, count in daily_stats:
            print(f"{day}: {count} orders")
            
        # 3. Check for Future Dates (Anomaly)
        future = session.query(func.count(OrderHeader.id)).filter(
            OrderHeader.shipped_at > datetime.now()
        ).scalar()
        print(f"\nOrders with FUTURE 'shipped_at' (Anomaly): {future}")

    finally:
        session.close()

if __name__ == "__main__":
    verify_outbound()
