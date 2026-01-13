import sys
import os
from datetime import date
import logging

# Add project root to python path
sys.path.append(os.getcwd())

# Disable logging to keep output clean
logging.disable(logging.CRITICAL)

from app.core import SessionLocal
from app.services.report_service import ReportService

def main():
    db = SessionLocal()
    try:
        # Focusing on Jan 9th, 2026 as it has verified data from all platforms
        target_date = date(2026, 1, 9)
        
        print(f"📦 Product Outbound Breakdown for: {target_date.strftime('%Y-%m-%d')}")
        print("=" * 80)
        print(f"{'SKU':<30} | {'Qty':<10} | {'Orders':<10} | {'Product Name'}")
        print("-" * 80)
        
        stats = ReportService.get_daily_outbound_stats(db, target_date)
        
        # stats['items'] contains the list of dicts with sku, product_name, total_qty, order_count
        items = stats.get('items', [])
        
        # Sort by Quantity descending
        items.sort(key=lambda x: x['total_qty'], reverse=True)
        
        for item in items[:20]: # Show top 20
            name = item['product_name'] or "Unknown"
            # Truncate long names
            if len(name) > 35:
                name = name[:32] + "..."
                
            print(f"{item['sku']:<30} | {item['total_qty']:<10} | {item['order_count']:<10} | {name}")
            
        print("-" * 80)
        print(f"Total Unique SKUs: {len(items)}")
        print(f"Total Shipped Items: {stats['total_items']}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
