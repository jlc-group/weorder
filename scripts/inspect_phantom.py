
import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

def inspect_phantom_data():
    db = SessionLocal()
    try:
        # Check Dec 31, 2025 to Jan 4, 2026
        # Note: timezone might be UTC in DB
        query = text("""
            SELECT channel_code, external_order_id, status_normalized, order_datetime, shipped_at, raw_payload, updated_at
            FROM order_header
            WHERE channel_code = 'lazada'
            AND shipped_at >= '2025-12-30 17:00:00' -- Dec 31 00:00 TH
            AND shipped_at <= '2026-01-01 17:00:00'   -- Jan 2 00:00 TH
            ORDER BY shipped_at ASC
        """)
        
        results = db.execute(query).fetchall()
        print(f"Found {len(results)} phantom orders:")
        
        for r in results:
            print(f"[{r.channel_code}] ID: {r.external_order_id} | Status: {r.status_normalized}")
            print(f"   Order Date: {r.order_datetime} | Shipped At: {r.shipped_at}")
            
            # Peek at raw payload for clues
            payload = r.raw_payload
            if r.channel_code == 'lazada':
                print(f"   Lazada UpdateTime: {payload.get('updated_at')}")
                print(f"   Lazada Promised: {payload.get('promised_shipping_times')}")
            elif r.channel_code == 'shopee':
                print(f"   Shopee Pickup: {payload.get('pickup_done_time')}")
                print(f"   Shopee Update: {payload.get('update_time')}")
            print("-" * 50)
            
    finally:
        db.close()

if __name__ == "__main__":
    inspect_phantom_data()
