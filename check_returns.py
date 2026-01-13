from app.core import get_db
from app.models.order import OrderHeader
from sqlalchemy import func

db = next(get_db())
results = db.query(
    OrderHeader.channel_code, 
    func.count(OrderHeader.id)
).filter(
    OrderHeader.status_normalized.in_(['RETURNED', 'TO_RETURN'])
).group_by(OrderHeader.channel_code).all()

print("Returns Count by Platform:")
for platform, count in results:
    print(f"{platform}: {count}")
