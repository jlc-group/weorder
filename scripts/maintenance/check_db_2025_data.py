import sys
import os
from datetime import datetime
from sqlalchemy import func, extract
from app.core import get_db, settings
from app.models import OrderHeader

# Add project root to path
sys.path.append(os.getcwd())

def check_2025_data():
    db = next(get_db())
    
    print("--- 2025 Data Verification ---")
    
    # Check total orders in 2025
    total_2025 = db.query(func.count(OrderHeader.id)).filter(
        extract('year', OrderHeader.order_datetime) == 2025
    ).scalar()
    print(f"Total Orders in 2025: {total_2025}")
    
    if total_2025 == 0:
        print("No data found for 2025.")
        return

    # Check earliest and latest order in 2025
    min_date = db.query(func.min(OrderHeader.order_datetime)).filter(
        extract('year', OrderHeader.order_datetime) == 2025
    ).scalar()
    
    max_date = db.query(func.max(OrderHeader.order_datetime)).filter(
        extract('year', OrderHeader.order_datetime) == 2025
    ).scalar()
    
    print(f"Earliest Order: {min_date}")
    print(f"Latest Order: {max_date}")
    
    # Group by month to finding missing months
    print("\n--- Monthly Breakdown ---")
    monthly_counts = db.query(
        extract('month', OrderHeader.order_datetime).label('month'),
        func.count(OrderHeader.id)
    ).filter(
        extract('year', OrderHeader.order_datetime) == 2025
    ).group_by('month').order_by('month').all()
    
    found_months = []
    for month, count in monthly_counts:
        month_int = int(month)
        found_months.append(month_int)
        print(f"Month {month_int}: {count} orders")
        
    missing_months = [m for m in range(1, 13) if m not in found_months]
    
    print("\n--- Summary ---")
    if not missing_months:
        print("✅ Data is complete for all 12 months of 2025.")
    else:
        print(f"⚠️ Missing data for months: {missing_months}")

if __name__ == "__main__":
    check_2025_data()
