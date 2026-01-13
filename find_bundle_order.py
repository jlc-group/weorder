import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from app.core.config import settings
from app.models import OrderHeader, OrderItem, Product

logging.basicConfig(level=logging.INFO)

def find_bundle_order():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Searching for orders with Bundles (Sets)...")
        
        # Join OrderItem -> Product. check product_type = 'SET'
        items = db.query(OrderItem).join(Product).filter(
            Product.product_type == 'SET'
        ).limit(5).all()
        
        if items:
            print("\n✅ Found Item with SET:")
            for item in items:
                print(f"Order ID: {item.order_id}")
                print(f"SKU: {item.sku}")
                print(f"Product Name: {item.product.name}")
                print(f"Components: {len(item.product.set_components)}")
                # Get Order external ID
                order = db.query(OrderHeader).get(item.order_id)
                if order:
                    print(f"External ID: {order.external_order_id}")
                    print("-" * 20)
        else:
            print("\n❌ No SET items found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    find_bundle_order()
