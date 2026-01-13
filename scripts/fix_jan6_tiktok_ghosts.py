import sys
import os
from sqlalchemy import cast, Date
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.order import OrderHeader

def fix_tiktok_ghosts():
    db = SessionLocal()
    target_date = '2026-01-06'
    
    print(f"--- Fixing TikTok Ghost Orders for {target_date} ---\n")
    
    # Find the ghosts
    ghosts = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'tiktok',
        cast(OrderHeader.shipped_at, Date) == target_date,
        OrderHeader.order_datetime < '2026-01-01'
    ).all()
    
    print(f"Found {len(ghosts)} ghost orders to fix.")
    
    fixed_count = 0
    for order in ghosts:
        # Prefer RTS time as shipped time, fallback to Delivery time, then Order time
        new_shipped_at = order.rts_time or order.delivery_time or order.order_datetime
        
        if new_shipped_at:
            order.shipped_at = new_shipped_at
            fixed_count += 1
            
            if fixed_count % 1000 == 0:
                print(f"Fixed {fixed_count} orders...")
                db.commit() # Commit periodically
    
    db.commit()
    print(f"\n✅ Successfully fixed timestamps for {fixed_count} orders.")
    db.close()

if __name__ == "__main__":
    fix_tiktok_ghosts()
