import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Product, ProductSetBom

logging.basicConfig(level=logging.INFO)

def cleanup_test_bundle():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # SKU we used: SET1_D1X2_190 (based on previous run)
        # But to be safe, find the SET product we modified
        # We know we created 'Test Component A (Serum)'
        
        c1 = db.query(Product).filter(Product.sku.like('COMP-SET1_D1X2_190-1')).first()
        if c1:
            # Find BOMs using this component
            boms = db.query(ProductSetBom).filter(ProductSetBom.component_product_id == c1.id).all()
            for bom in boms:
                # Get the set product
                set_prod = (db.query(Product).filter(Product.id == bom.set_product_id).first())
                if set_prod:
                    print(f"Reverting Product {set_prod.sku} to NORMAL")
                    set_prod.product_type = "NORMAL"
                db.delete(bom)
            
            # Commit BOM deletion first
            db.commit()
            print("Deleted BOMS for C1")
            
            # Now delete Component
            # Re-fetch c1 to be sure attached to session
            c1 = db.query(Product).filter(Product.sku.like('COMP-SET1_D1X2_190-1')).first()
            if c1:
                db.delete(c1)
                db.commit()
                print("Deleted Component 1")
            
        c2 = db.query(Product).filter(Product.sku.like('COMP-SET1_D1X2_190-2')).first()
        if c2:
             # Find BOMs for c2 as well just in case
             boms2 = db.query(ProductSetBom).filter(ProductSetBom.component_product_id == c2.id).all()
             for b in boms2:
                 db.delete(b)
             db.commit()
             
             c2 = db.query(Product).filter(Product.sku.like('COMP-SET1_D1X2_190-2')).first()
             if c2:
                 db.delete(c2)
                 db.commit()
                 print("Deleted Component 2")
             
        print("✅ Cleanup Complete")

    finally:
        db.close()

if __name__ == "__main__":
    cleanup_test_bundle()
