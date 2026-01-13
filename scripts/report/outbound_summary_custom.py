import sys
import os
from datetime import date, timedelta
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
        start_date = date(2025, 12, 31)
        end_date = date(2026, 1, 5)
        
        print(f"{'Date':<15} | {'Orders':<8} | {'Items':<8} | {'Shopee':<15} | {'Lazada':<15} | {'TikTok':<15}")
        print("-" * 90)
        
        current = start_date
        while current <= end_date:
            stats = ReportService.get_daily_outbound_stats(db, current)
            
            total_orders = stats['total_orders']
            total_items = stats['total_items']
            
            platforms = stats.get('platforms', {})
            shopee_stats = platforms.get('shopee', {'orders': 0, 'items': 0})
            lazada_stats = platforms.get('lazada', {'orders': 0, 'items': 0})
            tiktok_stats = platforms.get('tiktok', {'orders': 0, 'items': 0})
            
            shopee_str = f"{shopee_stats['orders']}/{shopee_stats['items']}"
            lazada_str = f"{lazada_stats['orders']}/{lazada_stats['items']}"
            tiktok_str = f"{tiktok_stats['orders']}/{tiktok_stats['items']}"
            
            print(f"{current.strftime('%Y-%m-%d'):<15} | {total_orders:<8} | {total_items:<8} | {shopee_str:<15} | {lazada_str:<15} | {tiktok_str:<15}")
            
            current += timedelta(days=1)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
