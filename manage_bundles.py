
import sys
import os
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
try:
    from app.core import settings
    from app.models.product import Product, ProductSetBom
except ImportError:
    pass

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def list_bundles():
    print("\n--- Bundle / Set Products ---")
    bundles = db.query(Product).filter(
        (Product.sku.like('DUO%')) | 
        (Product.sku.like('SET%')) | 
        (Product.sku.like('BUNDLE%')) | 
        (Product.product_type == 'SET')
    ).all()
    
    if not bundles:
        print("No bundles found.")
        return

    for p in bundles:
        components = db.query(ProductSetBom).filter(ProductSetBom.set_product_id == p.id).all()
        comp_str = ""
        if components:
            comp_list = []
            for c in components:
                c_prod = db.query(Product).get(c.component_product_id)
                comp_list.append(f"{c_prod.sku} (x{c.quantity})")
            comp_str = " -> " + ", ".join(comp_list)
        else:
            comp_str = " -> [NO RECIPE]"
            
        print(f"[{p.sku}] {p.name}{comp_str}")

def add_component(bundle_sku, component_sku, qty):
    print(f"\nMapping: {bundle_sku} + {qty} x {component_sku}")
    
    # 1. Find Bundle
    bundle = db.query(Product).filter(Product.sku == bundle_sku).first()
    if not bundle:
        print(f"Error: Bundle '{bundle_sku}' not found.")
        return
        
    # 2. Find Component
    comp = db.query(Product).filter(Product.sku == component_sku).first()
    if not comp:
        print(f"Error: Component '{component_sku}' not found.")
        return
        
    # 3. Check if exists
    existing = db.query(ProductSetBom).filter(
        ProductSetBom.set_product_id == bundle.id,
        ProductSetBom.component_product_id == comp.id
    ).first()
    
    if existing:
        print(f"Updating quantity from {existing.quantity} to {qty}")
        existing.quantity = qty
    else:
        print("Creating new mapping...")
        bom = ProductSetBom(
            set_product_id=bundle.id,
            component_product_id=comp.id,
            quantity=qty
        )
        db.add(bom)
        
    # Update type to SET just in case
    bundle.product_type = 'SET'
    
    db.commit()
    print("Success!")

def remove_component(bundle_sku, component_sku):
    print(f"\nRemoving: {component_sku} from {bundle_sku}")
    bundle = db.query(Product).filter(Product.sku == bundle_sku).first()
    comp = db.query(Product).filter(Product.sku == component_sku).first()
    
    if not bundle or not comp:
        print("Product not found.")
        return

    db.query(ProductSetBom).filter(
        ProductSetBom.set_product_id == bundle.id,
        ProductSetBom.component_product_id == comp.id
    ).delete()
    db.commit()
    print("Removed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Bundle Recipes")
    parser.add_argument('action', choices=['list', 'add', 'remove'], help='Action to perform')
    parser.add_argument('--bundle', '-b', help='Bundle SKU')
    parser.add_argument('--component', '-c', help='Component SKU')
    parser.add_argument('--qty', '-q', type=int, default=1, help='Quantity')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        list_bundles()
    elif args.action == 'add':
        if not args.bundle or not args.component:
            print("Error: --bundle and --component required for add")
        else:
            add_component(args.bundle, args.component, args.qty)
    elif args.action == 'remove':
        if not args.bundle or not args.component:
            print("Error: --bundle and --component required for remove")
        else:
            remove_component(args.bundle, args.component)
            
    db.close()
