from app.core import get_db
from app.models.order import OrderHeader
from app.models.finance import MarketplaceTransaction
from sqlalchemy import func, extract
import datetime

db = next(get_db())

print("=== Finance Data (MarketplaceTransaction) ===")
# Check if table has data
finance_count = db.query(func.count(MarketplaceTransaction.id)).scalar()
print(f"Total Finance Records: {finance_count}")

finance_by_platform = db.query(
    MarketplaceTransaction.platform,
    func.count(MarketplaceTransaction.id)
).group_by(MarketplaceTransaction.platform).all()

for p, c in finance_by_platform:
    print(f"  - {p}: {c}")

print("\n=== Order Counts (By Platform & Month) ===")
# Group by Platform, Year, Month
order_stats = db.query(
    OrderHeader.channel_code,
    extract('year', OrderHeader.order_datetime).label('year'),
    extract('month', OrderHeader.order_datetime).label('month'),
    func.count(OrderHeader.id)
).group_by(
    OrderHeader.channel_code,
    extract('year', OrderHeader.order_datetime),
    extract('month', OrderHeader.order_datetime)
).order_by(
    OrderHeader.channel_code,
    'year',
    'month'
).all()

for p, y, m, c in order_stats:
    if y is None or m is None:
        continue
    print(f"  - {p} {int(y)}-{int(m):02d}: {c} orders")
