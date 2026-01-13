
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
try:
    from app.core import settings
except ImportError:
    pass

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def audit_bundles():
    print("--- Auditing Bundles & DUO Sets ---")
    
    # 1. Search for DUO or SET SKUs in Product table
    q_products = """
        SELECT id, sku, name, product_type 
        FROM products 
        WHERE sku LIKE 'DUO%' OR sku LIKE 'SET%' OR sku LIKE 'BUNDLE%'
        LIMIT 10
    """
    products = db.execute(text(q_products)).fetchall()
    
    print(f"\nFound {len(products)} Sample Bundle/Sets:")
    for p in products:
        print(f"[{p[3]}] {p[1]} : {p[2]} (ID: {p[0]})")
        
        # 2. Check if they have components in 'set_components' (native mapping)
        # Assuming table is 'product_set_items' or similar? 
        # Let's check schemas via introspection if needed, or guess common names
        # Usually checking `product_components` or `product_sets`
    
    # 3. Check Platform Listings (External Mapping)
    # The current logic relies heavily on PlatformListing
    q_listings = """
        SELECT count(*) FROM platform_listings 
        WHERE platform_sku LIKE 'DUO%' OR platform_sku LIKE 'SET%'
    """
    listing_count = db.execute(text(q_listings)).scalar()
    print(f"\nPlatform Listings matching DUO/SET: {listing_count}")
    
    # 4. Deep dive into one logic
    if products:
        sample_id = products[0][0]
        # Check components
        # Likely table: product_components (parent_id, child_id, quantity)
        try:
            q_comps = """
                SELECT c.sku, c.name, pc.quantity 
                FROM product_components pc
                JOIN products c ON pc.component_id = c.id
                WHERE pc.product_id = :pid
            """
            comps = db.execute(text(q_comps), {"pid": sample_id}).fetchall()
            print(f"\nComponents for {products[0][1]}:")
            if comps:
                for c in comps:
                    print(f"  - {c[0]} (x{c[2]})")
            else:
                print("  - [NO COMPONENTS DEFINED]")
        except Exception as e:
            print(f"  (Error checking components table: {e})")

if __name__ == "__main__":
    audit_bundles()
    db.close()
