
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def analyze_platform_skus():
    """
    Query distinct SKUs sold on each platform based on existing Order Items
    """
    engine = create_engine(settings.DATABASE_URL)
    
    # Raw SQL is suitable for aggregation
    sql = """
    SELECT 
        oh.channel_code,
        oi.sku,
        COUNT(oi.id) as order_count,
        SUM(oi.quantity) as total_qty_sold,
        MAX(oi.product_name) as sample_name
    FROM order_header oh
    JOIN order_item oi ON oh.id = oi.order_id
    GROUP BY oh.channel_code, oi.sku
    ORDER BY oh.channel_code, order_count DESC;
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        
        # Group by platform
        platforms = {}
        for row in rows:
            channel = row.channel_code
            if channel not in platforms:
                platforms[channel] = []
            
            platforms[channel].append({
                "sku": row.sku,
                "count": row.order_count,
                "qty": row.total_qty_sold,
                "name": row.sample_name
            })
            
        return platforms

if __name__ == "__main__":
    results = analyze_platform_skus()
    
    print("\n=== Platform SKU Analysis ===\n")
    for platform, skus in results.items():
        print(f"Platform: {platform.upper()} (Total Distinct SKUs: {len(skus)})")
        print(f"{'SKU':<40} | {'Orders':<10} | {'Name (Sample)':<50}")
        print("-" * 100)
        
        # Show top 20
        for item in skus:
            print(f"{item['sku']:<40} | {item['count']:<10} | {item['name'][:50]}")
        print("\n")
