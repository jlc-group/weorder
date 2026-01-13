from sqlalchemy import create_engine, text
import time

# Use chanack user
DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

def count_jan2_orders():
    with engine.connect() as conn:
        # Count strictly what appears on the Jan 2nd Report (The metric user is watching)
        # Logic: COALESCE(shipped_at, updated_at) falls on Jan 2nd
        query_report = text("""
            SELECT count(*) 
            FROM order_header 
            WHERE 
                status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
                AND COALESCE(shipped_at, updated_at) >= '2026-01-02 00:00:00' 
                AND COALESCE(shipped_at, updated_at) < '2026-01-03 00:00:00'
        """)
        count_report = conn.execute(query_report).scalar()
        print(f"Orders currently showing on Jan 2nd Report: {count_report}")
        
        # Count progress (Fixed orders moved to 2025)
        query_moved = text("""
            SELECT count(*) 
            FROM order_header 
            WHERE 
                status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
                AND shipped_at < '2026-01-01 00:00:00'
        """)
        count_moved = conn.execute(query_moved).scalar()
        print(f"Total orders moved to 2025 (Corrected): {count_moved}")


if __name__ == "__main__":
    count_jan2_orders()
