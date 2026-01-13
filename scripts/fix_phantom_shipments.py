
import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

def fix_phantom_data():
    db = SessionLocal()
    try:
        # Move phantom shipments (Dec 31 - Jan 4) to Dec 30 (Last valid shipping day)
        target_date = '2025-12-30 18:00:00'
        
        # 1. Update Lazada/Shopee/TikTok orders in the phantom range
        # Only touch DELIVERED/SHIPPED status
        query = text(f"""
            UPDATE order_header
            SET shipped_at = '{target_date}'
            WHERE shipped_at >= '2025-12-30 17:00:00' -- Dec 31
            AND shipped_at <= '2026-01-04 23:59:59'   -- Jan 4 End
            AND status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
        """)
        
        result = db.execute(query)
        db.commit()
        
        print(f"Fixed {result.rowcount} phantom orders. Moved shipped_at to {target_date}.")
            
    finally:
        db.close()

if __name__ == "__main__":
    fix_phantom_data()
