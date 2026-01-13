import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.getcwd())
try:
    from app.core import settings
except ImportError:
    pass

def check():
    url = "postgresql://chanack:chanack@localhost:5432/weorder"
    try:
        from app.core import settings
        url = settings.DATABASE_URL
    except:
        pass
        
    print(f"Connecting to DB...")
    engine = create_engine(url)
    with engine.connect() as conn:
        print("\n=== Active Orders in DB (To Ship / Processing) ===")
        # Count by platform and status
        query = text("""
            SELECT channel_code, status_normalized, count(*)
            FROM order_header
            WHERE status_normalized IN ('NEW', 'PAID', 'PACKING', 'READY_TO_SHIP')
            GROUP BY channel_code, status_normalized
            ORDER BY channel_code, status_normalized
        """)
        result = conn.execute(query).fetchall()
        
        if not result:
            print("No active orders found in DB.")
        else:
            for row in result:
                print(f"{row[0]:<10} | {row[1]:<15} : {row[2]}")
        print("==================================================\n")

if __name__ == "__main__":
    check()
