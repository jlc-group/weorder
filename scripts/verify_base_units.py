import sys
import os
import re
from sqlalchemy import or_
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product

def verify_base_units():
    db = SessionLocal()
    try:
        # 1. Get potential bundles (X pattern)
        products = db.query(Product).filter(
            Product.sku.ilike('%X%'),
            Product.is_active == True,
            or_(Product.product_type == 'NORMAL', Product.product_type == None)
        ).all()
        
        print(f"Checking {len(products)} potential bundles for base units...\n")
        
        matches = []
        no_match = []
        
        # Regex to capture potentially the base SKU part before 'X'
        # e.g., C1-6GX6 -> Base: C1-6G, Qty: 6
        # Or C1-6G-X6
        pattern = re.compile(r'^(.+?)[-]?X(\d+)$', re.IGNORECASE)
        
        for p in products:
            match = pattern.search(p.sku)
            if match:
                base_sku_candidate = match.group(1)
                qty = int(match.group(2))
                
                # Try to find the base product
                base_product = db.query(Product).filter(Product.sku == base_sku_candidate).first()
                
                if base_product:
                    matches.append({
                        "bundle_sku": p.sku,
                        "bundle_name": p.name,
                        "base_sku": base_product.sku,
                        "base_name": base_product.name,
                        "qty": qty
                    })
                else:
                    # Sometimes the suffix might be different, e.g. C1-6G vs C1-6GX6 might not map perfectly if there's a dash diff
                    # Try removing last dash if present
                    if base_sku_candidate.endswith('-'):
                        clean_base = base_sku_candidate[:-1]
                        base_product = db.query(Product).filter(Product.sku == clean_base).first()
                        if base_product:
                            matches.append({
                                "bundle_sku": p.sku,
                                "bundle_name": p.name,
                                "base_sku": base_product.sku,
                                "base_name": base_product.name,
                                "qty": qty
                            })
                            continue
                            
                    no_match.append(f"{p.sku} (Base '{base_sku_candidate}' not found)")
            else:
                # Fallback for things like "SET_..." patterns that might not match X pattern
                pass
                
        # Sort and Display Matches
        print(f"✅ Found {len(matches)} automatic matches:\n")
        print(f"{'Bundle SKU':<30} | {'Qty':<5} | {'Base Unit SKU'}")
        print("-" * 80)
        for m in matches:
            print(f"{m['bundle_sku']:<30} | {m['qty']:<5} | {m['base_sku']}")
            
        print(f"\n❌ Could not automatically match {len(no_match)} items (Examples):")
        for nm in no_match[:10]:
            print(f" - {nm}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_base_units()
