import sys
import os
import re
from sqlalchemy import or_
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product, ProductSetBom

def migrate_confirmed_multipacks():
    db = SessionLocal()
    try:
        # 1. Get potential bundles (X pattern)
        # Using exact same logic as verify_base_units.py
        products = db.query(Product).filter(
            Product.sku.ilike('%X%'),
            Product.is_active == True,
            or_(Product.product_type == 'NORMAL', Product.product_type == None)
        ).all()
        
        print(f"Scanning {len(products)} candidates for migration...\n")
        
        pattern = re.compile(r'^(.+?)[-]?X(\d+)$', re.IGNORECASE)
        migrated_count = 0
        
        for p in products:
            match = pattern.search(p.sku)
            if match:
                base_sku_candidate = match.group(1)
                qty = int(match.group(2))
                
                # Try to find the base product
                base_product = db.query(Product).filter(Product.sku == base_sku_candidate).first()
                if not base_product and base_sku_candidate.endswith('-'):
                     base_product = db.query(Product).filter(Product.sku == base_sku_candidate[:-1]).first()

                if base_product:
                    print(f"Migrating {p.sku} -> SET (Component: {base_product.sku} x {qty})")
                    
                    # 1. Update Product Type
                    p.product_type = 'SET'
                    
                    # 2. Create BOM (Clear old if exists just in case)
                    db.query(ProductSetBom).filter(ProductSetBom.set_product_id == p.id).delete()
                    
                    new_bom = ProductSetBom(
                        set_product_id=p.id,
                        component_product_id=base_product.id,
                        quantity=qty
                    )
                    db.add(new_bom)
                    migrated_count += 1
        
        db.commit()
        print(f"\n✅ Successfully migrated {migrated_count} products to SET type.")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_confirmed_multipacks()
