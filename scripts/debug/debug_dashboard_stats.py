import sys
import os
from datetime import datetime
from app.core import get_db, settings
from app.services import OrderService
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.append(os.getcwd())

def test_dashboard_stats():
    # Create DB session
    db = next(get_db())
    
    print(f"Timezone: {settings.TIMEZONE}")
    
    # Test 1: Today (2026-01-01)
    print("\n--- Test 1: Today (2026-01-01) ---")
    stats = OrderService.get_dashboard_stats(db, start_date="2026-01-01", end_date="2026-01-01")
    print(f"Period Orders: {stats['period_orders']}")
    print(f"Period Revenue: {stats['period_revenue']}")
    print(f"Filter Info: {stats.get('filter_info')}")
    print(f"Debug Timezone: {stats.get('debug_timezone')}")
    
    # Test 2: This Month (2026-01-01 to 2026-01-01) - Initial state of "This Month"
    print("\n--- Test 2: This Month (2026-01-01 to 2026-01-01) ---")
    # In logic, if today is 1st, start of month is today
    stats_month = OrderService.get_dashboard_stats(db, start_date="2026-01-01", end_date="2026-01-01")
    print(f"Period Orders: {stats_month['period_orders']}")
    print(f"Sales Trend: {stats_month['sales_trend']}")

    # Test 3: Last Month (2025-12-01 to 2025-12-31)
    print("\n--- Test 3: Last Month (Dec 2025) ---")
    stats_dec = OrderService.get_dashboard_stats(db, start_date="2025-12-01", end_date="2025-12-31")
    print(f"Period Orders: {stats_dec['period_orders']}")
    print(f"Period Revenue: {stats_dec['period_revenue']}")
    print(f"Sales Trend Length: {len(stats_dec['sales_trend'])}")
    if len(stats_dec['sales_trend']) > 0:
        print(f"First Trend Date: {stats_dec['sales_trend'][0]}")
        print(f"Last Trend Date: {stats_dec['sales_trend'][-1]}")

if __name__ == "__main__":
    test_dashboard_stats()
