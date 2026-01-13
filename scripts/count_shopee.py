from app.core import get_db, SessionLocal
from app.models import OrderHeader
from sqlalchemy import func

def count_shopee():
    db = SessionLocal()
    try:
        count = db.query(func.count(OrderHeader.id)).filter(OrderHeader.channel_code == 'shopee').scalar()
        print(f"Total Shopee Orders: {count}")
        
        # Get latest date
        latest = db.query(func.max(OrderHeader.order_datetime)).filter(OrderHeader.channel_code == 'shopee').scalar()
        if latest:
            print(f"Latest Order Date: {latest}")
            
    finally:
        db.close()

if __name__ == "__main__":
    count_shopee()
