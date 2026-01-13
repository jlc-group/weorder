from app.core.database import SessionLocal
from app.models import OrderHeader
from sqlalchemy import func
from datetime import datetime, time, timezone

db = SessionLocal()

# range for 2025-01-02
target_date = datetime(2025, 1, 2).date() # Wait, is it 2025 or 2026? User said "January 2nd". Current year is 2026.
# If user meant Jan 2nd THIS MONTH, it is 2026-01-02.
# But context '5d82eca2...' implies fixing 2025 vs 2026 date logic.
# Let's check 2026-01-02 first as it is recent.

start_dt = datetime(2026, 1, 2, 0, 0, 0)
end_dt = datetime(2026, 1, 2, 23, 59, 59)

print(f"Checking for orders shipped between {start_dt} and {end_dt}")

# Query 1: Orders with shipped_at in range
shipped_on_date = db.query(OrderHeader).filter(
    OrderHeader.shipped_at >= start_dt,
    OrderHeader.shipped_at <= end_dt
).all()

print(f"\nOrders with shipped_at on Jan 2nd: {len(shipped_on_date)}")
for o in shipped_on_date[:5]:
    print(f" - {o.external_order_id} | Shipped: {o.shipped_at} | Updated: {o.updated_at}")

# Query 2: Orders with shipped_at NULL but updated_at in range (Fallback logic)
fallback_on_date = db.query(OrderHeader).filter(
    OrderHeader.shipped_at == None,
    OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'RETURNED', 'TO_RETURN', 'RETURN_INITIATED']),
    OrderHeader.updated_at >= start_dt,
    OrderHeader.updated_at <= end_dt
).all()

print(f"\nOrders using Fallback (updated_at) on Jan 2nd: {len(fallback_on_date)}")
for o in fallback_on_date[:5]:
    print(f" - {o.external_order_id} | Status: {o.status_normalized} | Updated: {o.updated_at} | Created: {o.created_at}")

# Query 3: Orders created on Jan 2nd (to distinguish if user is confusing created vs shipped)
created_on_date = db.query(OrderHeader).filter(
    OrderHeader.order_datetime >= start_dt,
    OrderHeader.order_datetime <= end_dt
).count()
print(f"\nOrders created on Jan 2nd: {created_on_date}")


db.close()
