import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import OrderHeader

logging.basicConfig(level=logging.INFO)

def find_printable_order():
    # Use DATABASE_URL as identified previously
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Searching for orders with printable labels...")
        
        # Check for AWAITING_COLLECTION (Ready to Ship)
        orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_raw == 'AWAITING_COLLECTION'
        ).limit(5).all()
        
        if orders:
            print("\n✅ Found 'AWAITING_COLLECTION' orders (Ready to Ship):")
            for o in orders:
                print(f"Internal ID: {o.id}\nExternal ID: {o.external_order_id}\nStatus: {o.status_raw}\n")
        else:
            print("\n❌ No 'AWAITING_COLLECTION' orders found.")
            
        # Check for IN_TRANSIT which implies shipped and label exists
        orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_raw == 'IN_TRANSIT'
        ).limit(5).all()
        
        if orders:
             print("\n✅ Found 'IN_TRANSIT' orders (Shipped):")
             for o in orders:
                print(f"Internal ID: {o.id}\nExternal ID: {o.external_order_id}\nStatus: {o.status_raw}\n")
        else:
            print("❌ No 'IN_TRANSIT' orders found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    find_printable_order()
