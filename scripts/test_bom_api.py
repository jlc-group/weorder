import sys
import os
from uuid import UUID
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product
from app.api.product_set import get_product_bom

def test_api_logic():
    db = SessionLocal()
    try:
        # Find our demo set
        set_sku = 'SET_SONGKRAN_C3C4_999'
        product = db.query(Product).filter(Product.sku == set_sku).first()
        
        if not product:
            print("Set product not found")
            return

        print(f"Testing GET BOM for {product.sku} ({product.id})")
        
        # Test the function directly
        result = get_product_bom(product.id, db)
        
        print(f"Success! Found {len(result)} components:")
        for item in result:
            print(f" - {item['sku']} x {item['quantity']}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_api_logic()
