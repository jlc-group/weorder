import sys
import os
from sqlalchemy import func
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product, ProductSetBom

def check_product_sets():
    db = SessionLocal()
    try:
        # Query ALL BOM relationships
        boms = db.query(ProductSetBom).all()
        
        if not boms:
            print("No BOM relationships found in the database.")
            return

        # Group by Set ID
        sets_map = {}
        for bom in boms:
            if bom.set_product_id not in sets_map:
                sets_map[bom.set_product_id] = []
            sets_map[bom.set_product_id].append(bom)
            
        print(f"Found {len(sets_map)} products with components defined.\n")
        
        for set_id, components in sets_map.items():
            set_product = db.query(Product).get(set_id)
            print(f"📦 Set: {set_product.sku} - {set_product.name} (Type: {set_product.product_type})")
            
            for bom in components:
                comp = db.query(Product).get(bom.component_product_id)
                print(f"   └── x{bom.quantity} {comp.sku} ({comp.name})")
            print("-" * 50)
                
    finally:
        db.close()

if __name__ == "__main__":
    check_product_sets()
