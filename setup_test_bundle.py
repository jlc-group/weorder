import logging
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import OrderItem, Product, ProductSetBom

logging.basicConfig(level=logging.INFO)

def setup_test_bundle():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Find an OrderItem to use
        item = db.query(OrderItem).first()
        if not item:
            print("No items found.")
            return

        sku = item.sku
        print(f"Using SKU: {sku} from Order: {item.order_id}")
        
        # 2. Find or Create Product
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            print("Creating Product...")
            product = Product(
                id=item.product_id or uuid4(), # Use item's product_id if exists
                sku=sku,
                name=item.product_name or f"Test Product {sku}",
                product_type="SET",
                is_active=True
            )
            db.add(product)
            db.commit() # Commit to get ID if needed
        else:
            print("Updating Product to SET...")
            product.product_type = "SET"
            db.commit()
            
        # Ensure item links to product
        if not item.product_id:
            item.product_id = product.id
            db.commit()

        # 3. Create Component Products
        comp1_sku = f"COMP-{sku}-1"
        comp2_sku = f"COMP-{sku}-2"
        
        c1 = db.query(Product).filter(Product.sku == comp1_sku).first()
        if not c1:
            c1 = Product(sku=comp1_sku, name="Test Component A (Serum)", product_type="NORMAL")
            db.add(c1)
            
        c2 = db.query(Product).filter(Product.sku == comp2_sku).first()
        if not c2:
            c2 = Product(sku=comp2_sku, name="Test Component B (Soap)", product_type="NORMAL")
            db.add(c2)
        
        db.commit()
        
        # 4. Link BOM
        # Clear existing
        db.query(ProductSetBom).filter(ProductSetBom.set_product_id == product.id).delete()
        
        bom1 = ProductSetBom(set_product_id=product.id, component_product_id=c1.id, quantity=1)
        bom2 = ProductSetBom(set_product_id=product.id, component_product_id=c2.id, quantity=2)
        
        db.add(bom1)
        db.add(bom2)
        db.commit()
        
        print(f"✅ Setup Complete. SKU '{sku}' is now a SET with 2 components.")
        print(f"Test Order ID: {item.order_id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_bundle()
