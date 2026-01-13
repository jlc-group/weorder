
import sys
import os
from sqlalchemy import text

# Add project root to path (assuming script is run from project root)
sys.path.append(os.getcwd())

from app.core import get_db

def check_orders():
    db = next(get_db())
    try:
        sql = """
            SELECT 
                EXTRACT(MONTH FROM order_datetime) as month, 
                COUNT(*) as count 
            FROM order_header 
            WHERE EXTRACT(YEAR FROM order_datetime) = 2025 
            AND channel_code = 'shopee'
            GROUP BY month 
            ORDER BY month
        """
        result = db.execute(text(sql)).fetchall()
        
        print("\n--- Shopee Orders 2025 Distribution ---")
        found_months = {}
        for row in result:
            month = int(row[0])
            count = row[1]
            found_months[month] = count
            print(f"Month {month}: {count} orders")
            
        print("\n--- Missing Months ---")
        for m in range(1, 13):
            if m not in found_months:
                print(f"Month {m}: 0 orders (Needs Sync)")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_orders()
