import sys
import os
import re
from sqlalchemy import or_
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product, ProductSetBom

def create_missing_bases_and_migrate():
    db = SessionLocal()
    try:
        # Same logic to find candidates
        products = db.query(Product).filter(
            Product.sku.ilike('%X%'),
            Product.is_active == True,
            or_(Product.product_type == 'NORMAL', Product.product_type == None)
        ).all()
        
        pattern = re.compile(r'^(.+?)[-]?X(\d+)$', re.IGNORECASE)
        
        created_bases = 0
        migrated_count = 0
        
        print(f"Scanning {len(products)} remaining candidates...")

        for p in products:
            match = pattern.search(p.sku)
            if match:
                base_sku_candidate = match.group(1)
                qty = int(match.group(2))
                
                # Check if base exists
                base_product = db.query(Product).filter(Product.sku == base_sku_candidate).first()
                
                # If not found, try removing trailing dash
                if not base_product and base_sku_candidate.endswith('-'):
                     base_sku_candidate = base_sku_candidate[:-1]
                     base_product = db.query(Product).filter(Product.sku == base_sku_candidate).first()

                # If STILL not found, CREATE IT
                if not base_product:
                    print(f"Creating missing base unit: {base_sku_candidate}")
                    
                    # Create the base product
                    base_product = Product(
                        sku=base_sku_candidate,
                        name=f"{p.name} (Unit)", # Best effort name
                        product_type='NORMAL',
                        is_active=True,
                        standard_cost=0, # Default
                        standard_price=0
                    )
                    db.add(base_product)
                    db.flush() # distinct flush to get ID
                    created_bases += 1

                # Now migrate the multipack
                print(f"Migrating {p.sku} -> SET (Component: {base_product.sku} x {qty})")
                
                p.product_type = 'SET'
                
                # Clear old BOM
                db.query(ProductSetBom).filter(ProductSetBom.set_product_id == p.id).delete()
                
                new_bom = ProductSetBom(
                    set_product_id=p.id,
                    component_product_id=base_product.id,
                    quantity=qty
                )
                db.add(new_bom)
                migrated_count += 1
        
        db.commit()
        print(f"\n✅ Created {created_bases} new base units.")
        print(f"✅ Migrated {migrated_count} additional multipacks to Sets.")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_missing_bases_and_migrate()
