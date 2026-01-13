
import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

def diagnose_jan5():
    db = SessionLocal()
    try:
        # 1. Shipped Count
        shipped_count = db.execute(text("""
            SELECT count(*) FROM order_header 
            WHERE shipped_at >= '2026-01-05 00:00:00' 
            AND shipped_at <= '2026-01-05 23:59:59'
        """)).scalar()
        
        # 2. Created Count (Might be orders created earlier but shipped Jan 5)
        # But also check orders created ON Jan 5
        created_count = db.execute(text("""
            SELECT count(*) FROM order_header 
            WHERE order_datetime >= '2026-01-05 00:00:00' 
            AND order_datetime <= '2026-01-05 23:59:59'
        """)).scalar()
        
        # 3. Check for "Pending/Shipped" orders with NO shipped_at
        missing_date_count = db.execute(text("""
            SELECT count(*) FROM order_header
            WHERE status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
            AND shipped_at IS NULL
        """)).scalar()
        
        # 4. Platform Breakdown for Jan 5 Shipped
        breakdown = db.execute(text("""
            SELECT channel_code, count(*) 
            FROM order_header 
            WHERE shipped_at >= '2026-01-05 00:00:00' 
            AND shipped_at <= '2026-01-05 23:59:59'
            GROUP BY channel_code
        """)).fetchall()
        
        print(f"--- Jan 5, 2026 Diagnosis ---")
        print(f"Shipped Count: {shipped_count} (User Expects >16,000)")
        print(f"Created Count: {created_count}")
        print(f"Shipped/Delivered Orders with NULL date (Total): {missing_date_count}")
        print(f"Breakdown: {breakdown}")
        
    finally:
        db.close()

if __name__ == "__main__":
    diagnose_jan5()
