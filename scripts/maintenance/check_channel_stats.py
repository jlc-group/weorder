import sys
import os
from sqlalchemy import func, extract
from app.core import get_db
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader

# Add project root to path
sys.path.append(os.getcwd())

def check_channel_stats():
    db = next(get_db())
    print("--- 2025 Order Stats by Channel ---")
    
    stats = db.query(
        OrderHeader.channel_code,
        func.count(OrderHeader.id)
    ).filter(
        extract('year', OrderHeader.order_datetime) == 2025
    ).group_by(OrderHeader.channel_code).all()
    
    total = 0
    for channel, count in stats:
        print(f"Channel: {channel.upper()} -> {count} orders")
        total += count
        
    print(f"Total 2025 Orders: {total}")
    
    # Check monthly breakdown for Shopee specifically
    print("\n--- Shopee Monthly Breakdown (2025) ---")
    shopee_monthly = db.query(
        extract('month', OrderHeader.order_datetime).label('month'),
        func.count(OrderHeader.id)
    ).filter(
        extract('year', OrderHeader.order_datetime) == 2025,
        OrderHeader.channel_code == 'shopee'
    ).group_by('month').order_by('month').all()
    
    for month, count in shopee_monthly:
        print(f"Month {int(month)}: {count}")

if __name__ == "__main__":
    check_channel_stats()
