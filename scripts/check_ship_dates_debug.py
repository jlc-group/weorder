from app.core.database import SessionLocal
from app.models import OrderHeader
from sqlalchemy import desc

db = SessionLocal()

# Get orders shipped/delivered recently
orders = db.query(OrderHeader).filter(
    OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'RETURNED', 'TO_RETURN', 'RETURN_INITIATED'])
).order_by(desc(OrderHeader.order_datetime)).limit(5).all()

print(f"{'External ID':<20} | {'Status':<15} | {'Order Date (Local)':<20} | {'Shipped At (Local)':<20} | {'Updated At (Local)':<20}")
print("-" * 105)

for o in orders:
    shipped = o.shipped_at.strftime('%Y-%m-%d %H:%M') if o.shipped_at else "None"
    updated = o.updated_at.strftime('%Y-%m-%d %H:%M') if o.updated_at else "None"
    ordered = o.order_datetime.strftime('%Y-%m-%d %H:%M') if o.order_datetime else "None"
    print(f"{o.external_order_id:<20} | {o.status_normalized:<15} | {ordered:<20} | {shipped:<20} | {updated:<20}")

db.close()
