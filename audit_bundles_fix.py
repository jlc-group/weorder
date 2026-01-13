
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
# Use app.core.settings for reliable connection
from app.core import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def audit_bundles():
    print("--- Auditing Bundles & DUO Sets (Retry) ---")
    
    # 1. Search for Sample DUO/SET/BUNDLE
    q_products = """
        SELECT id, sku, name, product_type 
        FROM products 
        WHERE sku LIKE 'DUO%' OR sku LIKE 'SET%' OR sku LIKE 'BUNDLE%'
        LIMIT 5
    """
    products = db.execute(text(q_products)).fetchall()
    
    print(f"\nFound {len(products)} Sample Bundle/Sets:")
    for p in products:
        print(f"[{p[3]}] {p[1]} : {p[2]} (ID: {p[0]})")
        
        # 2. Check Native Components (product_components / product_set_items ?)
        # I need to know the table name for components. 
        # I suspect `product_sets` or `set_components`.
        # Let's try introspection
        try:
           q_comps = """
                SELECT c.sku, c.name, psi.quantity 
                FROM product_sets psi
                JOIN products c ON psi.product_child_id = c.id
                WHERE psi.product_parent_id = :pid
           """ 
           # Note: Table name `product_sets` is a guess based on router `app/api/product_set.py`
           
           comps = db.execute(text(q_comps), {"pid": p[0]}).fetchall()
           if comps:
               print("  -> Built-in Components:")
               for c in comps:
                   print(f"     - {c[0]} (x{c[2]})")
           else:
               print("  -> [NO BUILT-IN COMPONENTS]")
        except Exception as e:
            # Maybe table doesn't exist?
            pass

    # 3. Check Platform Listings (External Mapping)
    print("\n--- Platform Listings (Bundle Maps) ---")
    q_listings = """
        SELECT platform, platform_sku, count(id) as item_count
        FROM platform_listings
        WHERE platform_sku LIKE 'DUO%' OR platform_sku LIKE 'SET%'
        GROUP BY platform, platform_sku
        LIMIT 5
    """
    try:
        listings = db.execute(text(q_listings)).fetchall()
        for l in listings:
            print(f"- {l[0]} | {l[1]} | Has {l[2]} component entry(s)")
            
            # Show details for the first one
            q_detail = """
                SELECT p.sku, pli.quantity
                FROM platform_listing_items pli
                JOIN platform_listings pl ON pli.listing_id = pl.id
                JOIN products p ON pli.product_id = p.id
                WHERE pl.platform_sku = :psku AND pl.platform = :plat
            """
            details = db.execute(text(q_detail), {"psku": l[1], "plat": l[0]}).fetchall()
            for d in details:
                print(f"   -> {d[0]} x {d[1]}")
    except Exception as e:
        print(f"Error checking platform listings: {e}")

if __name__ == "__main__":
    audit_bundles()
    db.close()
