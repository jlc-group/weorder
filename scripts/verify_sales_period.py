import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_sales():
    print(f"Connecting to DB: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else '...'}")
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("\n=== Sales Summary (2025-12-30 to Present) ===")
        
        # Total per platform
        query = text("""
            SELECT 
                channel_code, 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status_normalized != 'CANCELLED' THEN total_amount ELSE 0 END) as valid_revenue,
                COUNT(CASE WHEN status_normalized = 'CANCELLED' THEN 1 END) as cancelled_count
            FROM order_header
            WHERE order_datetime >= '2025-12-30 00:00:00'
            GROUP BY channel_code
            ORDER BY channel_code
        """)
        
        try:
            result = conn.execute(query).fetchall()
            if not result:
                print("No data found for this period.")
            
            for row in result:
                # row: channel, total, revenue, cancelled
                print(f"Platform: {row[0].ljust(10)} | Orders: {str(row[1]).rjust(5)} | Rev: {float(row[2] or 0):,.2f} | Canceled: {row[3]}")
                
        except Exception as e:
            print(f"Error executing summary query: {e}")

        print("\n--- Daily Breakdown ---")
        query_daily = text("""
            SELECT 
                DATE(order_datetime) as date,
                channel_code,
                COUNT(*) as count,
                SUM(CASE WHEN status_normalized != 'CANCELLED' THEN total_amount ELSE 0 END) as revenue
            FROM order_header
            WHERE order_datetime >= '2025-12-30 00:00:00'
            GROUP BY DATE(order_datetime), channel_code
            ORDER BY date DESC, channel_code
        """)
        
        try:
            result_daily = conn.execute(query_daily).fetchall()
            for row in result_daily:
                print(f"{row[0]} | {row[1].ljust(10)} | Count: {str(row[2]).ljust(4)} | Rev: {float(row[3] or 0):,.2f}")
        except Exception as e:
            print(f"Error executing daily query: {e}")

if __name__ == "__main__":
    check_sales()
