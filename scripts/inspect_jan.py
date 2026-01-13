
import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

def inspect_jan_data():
    db = SessionLocal()
    try:
        # Check Jan 4 to Jan 6
        query = text("""
            SELECT channel_code, external_order_id, status_normalized, order_datetime, shipped_at, raw_payload
            FROM order_header
            WHERE shipped_at >= '2026-01-04 00:00:00'
            AND shipped_at <= '2026-01-06 23:59:59'
            ORDER BY shipped_at ASC
        """)
        
        results = db.execute(query).fetchall()
        print(f"Found {len(results)} orders between Jan 4 - Jan 6:")
        
        counts = {}
        for r in results:
            date_str = str(r.shipped_at.date())
            if date_str not in counts: counts[date_str] = 0
            counts[date_str] += 1
            
        print("Counts per day:", counts)
        
        print("\nSample Data:")
        for r in results[:5]:
            print(f"[{r.channel_code}] {r.external_order_id} | Shipped: {r.shipped_at}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_jan_data()
