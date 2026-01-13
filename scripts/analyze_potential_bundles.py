import sys
import os
import re
from sqlalchemy import or_
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.product import Product

def analyze_bundles():
    db = SessionLocal()
    try:
        # Get all active products that are NOT already configured as SET
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(Product.product_type == 'NORMAL', Product.product_type == None)
        ).all()
        
        print(f"Scanning {len(products)} active products for potential bundles...\n")
        
        potential_bundles = []
        
        # Regex patterns
        # Matches SKUs like ...X2..., ...X10...
        sku_qty_pattern = re.compile(r'X(\d+)', re.IGNORECASE)
        # Matches names with "Pack 3", "Set 2", etc.
        name_pack_pattern = re.compile(r'(?:Pack|Set)\s*(\d+)', re.IGNORECASE)
        
        for p in products:
            is_suspicious = False
            reason = []
            
            # check SKU pattern
            sku_match = sku_qty_pattern.search(p.sku)
            if sku_match:
                qty = int(sku_match.group(1))
                if qty > 1:
                    is_suspicious = True
                    reason.append(f"SKU contains 'X{qty}'")

            # Check Name keywords
            lower_name = p.name.lower()
            if 'แถม' in lower_name or 'free' in lower_name:
                 is_suspicious = True
                 reason.append("Contains 'Free/แถม'")
            
            if 'pack' in lower_name or 'แพ็ค' in lower_name:
                 is_suspicious = True
                 reason.append("Contains 'Pack'")
                 
            if 'set' in lower_name or 'เซ็ต' in lower_name:
                 is_suspicious = True
                 reason.append("Contains 'Set'")
                 
            # Check for quantity indicators in text usually implies bundle
            # e.g. "2 หลอด", "6 ซอง", "1 กล่อง" (Box often implies unit, but sometimes bundle if SKU is different)
            
            if is_suspicious:
                potential_bundles.append({
                    "sku": p.sku,
                    "name": p.name,
                    "reasons": ", ".join(reason)
                })
        
        # Sort by SKU for readability
        potential_bundles.sort(key=lambda x: x['sku'])
        
        print(f"Found {len(potential_bundles)} potential unconfigured bundles:\n")
        
        print(f"{'SKU':<30} | {'Reasons':<30} | {'Name'}")
        print("-" * 100)
        
        for item in potential_bundles[:30]: # Limit output
             # Truncate name
            name = (item['name'][:50] + '..') if len(item['name']) > 50 else item['name']
            print(f"{item['sku']:<30} | {item['reasons']:<30} | {name}")
            
    finally:
        db.close()

if __name__ == "__main__":
    analyze_bundles()
