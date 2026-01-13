import sys
import os
from sqlalchemy import cast, Date, func
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.order import OrderHeader

def analyze_jan6():
    db = SessionLocal()
    target_date = '2026-01-06'
    
    print(f"--- Analysis for {target_date} ---\n")
    
    # 1. Total Count by Channel
    results = db.query(
        OrderHeader.channel_code, 
        func.count(OrderHeader.id)
    ).filter(
        cast(OrderHeader.shipped_at, Date) == target_date
    ).group_by(OrderHeader.channel_code).all()
    
    print("Total Orders Shipped:")
    for channel, count in results:
        print(f" - {channel}: {count}")
        
    # 2. Analyze TikTok anomaly (Recovering real dates?)
    print("\n--- TikTok Ghost Analysis ---")
    ghosts = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'tiktok',
        cast(OrderHeader.shipped_at, Date) == target_date,
        OrderHeader.order_datetime < '2026-01-01'
    ).limit(10).all()
    
    print("Checking timestamps for TikTok Ghosts:")
    for g in ghosts:
        print(f" - OrdID: {g.external_order_id}")
        print(f"   OrderDate: {g.order_datetime}")
        print(f"   ShippedAt (Current): {g.shipped_at}")
        print(f"   RTS Time: {g.rts_time}")
        print(f"   Delivery Time: {g.delivery_time}")
        print(f"   PL Discount: {g.platform_discount_amount}")

    # 3. Analyze Lazada (Any activity?)
    print("\n--- Lazada Activity Check ---")
    lazada_any = db.query(OrderHeader).filter(
        OrderHeader.channel_code == 'lazada',
        cast(OrderHeader.updated_at, Date) == target_date
    ).limit(10).all()
    
    print(f"Any Lazada updates on Jan 6? Found: {len(lazada_any)} (showing first few)")
    for l in lazada_any:
         print(f" - {l.external_order_id} | Status: {l.status_normalized} | Updated: {l.updated_at}")
         
    db.close()

if __name__ == "__main__":
    analyze_jan6()
