import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from sqlalchemy import func
from datetime import datetime
from app.core.database import SessionLocal
from app.models.order import OrderHeader

def check_december_orders():
    db = SessionLocal()
    try:
        # Define date range: 2025-12-01 to 2026-01-01
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2026, 1, 1)

        print(f"Querying orders from {start_date} to {end_date}...")

        # Count orders
        count = db.query(OrderHeader).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date
        ).count()

        # Sum total amount
        total_amount = db.query(func.sum(OrderHeader.total_amount)).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date
        ).scalar()

        print(f"\nResults for December 2025:")
        print(f"Total Orders: {count}")
        print(f"Total Amount: {total_amount:,.2f} THB" if total_amount else "Total Amount: 0.00 THB")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_december_orders()
