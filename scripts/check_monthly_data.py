import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path to import app modules
sys.path.append(os.getcwd())

from app.core import settings

def check_monthly_data_by_platform():
    engine = create_engine(settings.DATABASE_URL)
    
    query = text("""
        SELECT 
            TO_CHAR(order_datetime, 'YYYY-MM') as month,
            channel_code,
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue
        FROM order_header
        WHERE status_normalized NOT IN ('CANCELLED', 'RETURNED')
        GROUP BY TO_CHAR(order_datetime, 'YYYY-MM'), channel_code
        ORDER BY month DESC, total_revenue DESC;
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
        print(f"{'Month':<10} | {'Platform':<15} | {'Orders':<10} | {'Revenue':<15}")
        print("-" * 60)
        
        current_month = None
        for row in rows:
            month = row[0]
            platform = row[1] or "Unknown"
            count = row[2]
            revenue = float(row[3]) if row[3] else 0
            
            if current_month != month:
                if current_month is not None:
                    print("-" * 60)
                current_month = month
                
            print(f"{month:<10} | {platform:<15} | {count:<10} | {revenue:,.2f}")
            
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    check_monthly_data_by_platform()
