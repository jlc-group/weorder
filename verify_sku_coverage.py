
import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

def verify_coverage():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n=== SKU Coverage Analysis ===\n")
        
        # 1. Total Master Products
        res_products = conn.execute(text("SELECT COUNT(*), COUNT(CASE WHEN is_active THEN 1 END) FROM product"))
        total_prod, active_prod = res_products.fetchone()
        print(f"Master Products (DB): {total_prod} (Active: {active_prod})")
        
        # 2. Total Platform Listings
        res_listings = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT platform_sku) FROM platform_listing"))
        total_listings, distinct_platform_skus = res_listings.fetchone()
        print(f"Platform Listings: {total_listings} (Distinct SKUs: {distinct_platform_skus})")
        
        # 3. Mapped Master Products (How many master products are linked to at least one listing?)
        sql_mapped = """
        SELECT COUNT(DISTINCT product_id) 
        FROM platform_listing_item
        """
        mapped_count = conn.execute(text(sql_mapped)).scalar()
        print(f"Mapped Master Products: {mapped_count} ({(mapped_count/total_prod*100):.1f}% coverage)")
        
        # 4. Historical Sold SKUs vs Listings (Are there sold SKUs missing from listings?)
        sql_missed_sales = """
        SELECT 
            oh.channel_code,
            oi.sku,
            COUNT(*) as times_sold
        FROM order_item oi
        JOIN order_header oh ON oi.order_id = oh.id
        LEFT JOIN platform_listing pl ON pl.platform = oh.channel_code AND pl.platform_sku = oi.sku
        WHERE pl.id IS NULL
        GROUP BY oh.channel_code, oi.sku
        ORDER BY times_sold DESC
        """
        missed = conn.execute(text(sql_missed_sales)).fetchall()
        
        print("\n--- SKUs sold in history but MISSING from Platform Listings ---")
        if not missed:
            print("NONE (All historical sales are covered!)")
        else:
            for row in missed:
                print(f"[{row[0]}] {row[1]} (Sold {row[2]} times)")
                
        # 5. Unmapped Active Master Products (Products we have but never listed/sold?)
        print("\n--- Active Master Products NOT in any Platform Listing (Potential Missing) ---")
        sql_orphan_master = """
        SELECT p.sku, p.name 
        FROM product p
        LEFT JOIN platform_listing_item pli ON p.id = pli.product_id
        WHERE p.is_active = true AND pli.id IS NULL
        LIMIT 20
        """
        orphans = conn.execute(text(sql_orphan_master)).fetchall()
        if not orphans:
             print("NONE")
        else:
             for row in orphans:
                 print(f"{row[0]:<20} | {row[1][:50]}")
             print(f"... and maybe more")

if __name__ == "__main__":
    verify_coverage()
