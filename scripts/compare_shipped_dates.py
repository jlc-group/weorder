
import sys
import os
from sqlalchemy import func
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader

def compare_dates():
    session = SessionLocal()
    try:
        # Check orders with shipped_at on Jan 5
        # But look at their updated_at (DB update time)
        # If updated_at is MUCH later (e.g. today Jan 7), it means we just backfilled them
        # BUT the valid value came from API.
        
        # We want to check if date(shipped_at) matches date(updated_at) roughly
        # Or if there's a pattern.
        
        target_date = datetime(2026, 1, 5)
        
        print(f"checking orders shipped on {target_date.date()}...")
        
        orders = session.query(
            OrderHeader.external_order_id,
            OrderHeader.shipped_at,
            OrderHeader.updated_at,
            OrderHeader.status_normalized
        ).filter(
            OrderHeader.shipped_at >= datetime(2026, 1, 5),
            OrderHeader.shipped_at < datetime(2026, 1, 6)
        ).limit(20).all()
        
        print(f"{'Order ID':<20} | {'Shipped At':<20} | {'Updated At':<20} | {'Status'}")
        print("-" * 75)
        for o in orders:
            print(f"{o.external_order_id:<20} | {o.shipped_at} | {o.updated_at} | {o.status_normalized}")

    finally:
        session.close()

if __name__ == "__main__":
    compare_dates()
