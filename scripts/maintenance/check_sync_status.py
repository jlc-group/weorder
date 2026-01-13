import sys
import os
from sqlalchemy import func, desc
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import SyncJob, PlatformConfig
from app.models.order import OrderHeader

def check_system_status():
    db = SessionLocal()
    try:
        print("=== 1. SYNC JOB HISTORY (Last 10) ===")
        jobs = db.query(SyncJob).order_by(desc(SyncJob.started_at)).limit(10).all()
        for job in jobs:
            print(f"[{job.started_at}] Type: {job.job_type}, Status: {job.status}")
            print(f"   Fetched: {job.orders_fetched}, Created: {job.orders_created}, Updated: {job.orders_updated}")
            if job.error_message:
                print(f"   ERROR: {job.error_message}")
        
        print("\n=== 2. PLATFORM CONFIG ===")
        configs = db.query(PlatformConfig).all()
        for config in configs:
            print(f"Platform: {config.platform}, Shop: {config.shop_name}")
            print(f"   Active: {config.is_active}, Sync Enabled: {config.sync_enabled}")
            print(f"   Last Sync: {config.last_sync_at}")
            
        print("\n=== 3. ORDER DATE DISTRIBUTION ===")
        # Get min and max order dates
        min_date = db.query(func.min(OrderHeader.order_datetime)).scalar()
        max_date = db.query(func.max(OrderHeader.order_datetime)).scalar()
        print(f"Min Order Date: {min_date}")
        print(f"Max Order Date: {max_date}")
        
        # Count orders per day for Dec 2025
        print("\nDaily Breakdown (Dec 2025):")
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2026, 1, 1)
        
        daily = db.query(
            func.date(OrderHeader.order_datetime).label('date'),
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime < end_date
        ).group_by('date').order_by('date').all()
        
        for date, count in daily:
            print(f"  {date}: {count}")

        # Count orders for Jan 2026 to see if they are landing there?
        print("\nDaily Breakdown (Jan 2026):")
        start_date_jan = datetime(2026, 1, 1)
        daily_jan = db.query(
            func.date(OrderHeader.order_datetime).label('date'),
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= start_date_jan
        ).group_by('date').order_by('date').all()
        
        for date, count in daily_jan:
            print(f"  {date}: {count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_system_status()
