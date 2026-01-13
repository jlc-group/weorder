
import sys
import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
from app.core import settings
from app.models import OrderHeader

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def backfill_rts():
    target_date = date(2026, 1, 11)
    print(f"--- Backfilling rts_time for {target_date} ---")
    
    try:
        tz = ZoneInfo(settings.TIMEZONE)
    except:
        tz = ZoneInfo("UTC")

    start_local = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    end_local = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    # Find orders that were "handled" on Jan 11
    # Either shipped_at is on Jan 11 OR updated_at is on Jan 11 and status is relevant
    orders = db.query(OrderHeader).filter(
        OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED', 'PENDING', 'UNPAID']),
        or_(
            # Case 1: Shipped on Jan 11
            func.coalesce(OrderHeader.shipped_at, OrderHeader.updated_at) >= start_utc
        ),
        or_(
            func.coalesce(OrderHeader.shipped_at, OrderHeader.updated_at) <= end_utc
        )
    ).all()

    print(f"Found {len(orders)} orders to process.")
    
    count = 0
    for order in orders:
        if not order.rts_time:
            # Anchor to the first known fulfillment event
            # Use shipped_at if available, else updated_at
            order.rts_time = order.shipped_at or order.updated_at
            count += 1
            
    db.commit()
    print(f"Done! Updated rts_time for {count} orders.")

if __name__ == "__main__":
    backfill_rts()
    db.close()
