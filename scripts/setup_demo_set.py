import sys
import os
from sqlalchemy import func
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product, ProductSetBom

def configure_demo_set():
    db = SessionLocal()
    try:
        # 1. Get the Set Product
        set_sku = 'SET_SONGKRAN_C3C4_999'
        set_product = db.query(Product).filter(Product.sku == set_sku).first()
        
        if not set_product:
            print(f"Set product {set_sku} not found!")
            return

        print(f"Found Set: {set_product.name}")
        
        # 2. Get Component Products (Best guess based on names)
        # "กันแดดเมลอน 1 กล่อง"" -> L10-30G
        # "เซรั่มขิงดำซิงก์ 1 กล่อง" -> C4-35G
        
        comp_melon = db.query(Product).filter(Product.sku == 'L10-30G').first()
        comp_ginger = db.query(Product).filter(Product.sku == 'C4-35G').first()
        
        if not comp_melon or not comp_ginger:
            print("Could not find components!")
            return
            
        print(f"Component 1: {comp_melon.sku} - {comp_melon.name}")
        print(f"Component 2: {comp_ginger.sku} - {comp_ginger.name}")
        
        # 3. Update Set Product Type
        set_product.product_type = 'SET'
        
        # 4. Create BOM Entries
        # Clear existing just in case
        db.query(ProductSetBom).filter(ProductSetBom.set_product_id == set_product.id).delete()
        
        bom1 = ProductSetBom(
            set_product_id=set_product.id,
            component_product_id=comp_melon.id,
            quantity=1
        )
        bom2 = ProductSetBom(
            set_product_id=set_product.id,
            component_product_id=comp_ginger.id,
            quantity=1
        )
        
        db.add(bom1)
        db.add(bom2)
        db.commit()
        
        print("\n✅ Successfully configured set!")
        print(f"Updated {set_product.sku} to type 'SET'")
        print(f"Added components:\n - {comp_melon.sku} (x1)\n - {comp_ginger.sku} (x1)")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    configure_demo_set()
