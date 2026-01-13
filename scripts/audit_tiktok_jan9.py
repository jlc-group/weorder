#!/usr/bin/env python3
"""
Audit TikTok Jan 9 orders.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader
from app.services import integration_service

TZ = ZoneInfo("Asia/Bangkok")

async def main():
    db = SessionLocal()
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == "tiktok").first()
    client = integration_service.get_client_for_config(config)
    
    # Jan 9 UTC
    start_utc = datetime(2026, 1, 8, 17, 0, 0, tzinfo=timezone.utc)
    end_utc = datetime(2026, 1, 9, 16, 59, 59, tzinfo=timezone.utc)
    
    print("Fetching Jan 9 orders (first 200)...")
    result = await client.get_orders(time_from=start_utc, time_to=end_utc, page_size=100)
    orders = result.get("orders", [])
    
    # Fetch next page too
    if result.get("next_cursor"):
        res2 = await client.get_orders(time_from=start_utc, time_to=end_utc, cursor=result["next_cursor"], page_size=100)
        orders.extend(res2.get("orders", []))
        
    print(f"Checking {len(orders)} orders against DB...")
    
    missing = 0
    wrong_date = 0
    correct = 0
    
    for api_order in orders:
        order_id = api_order.get("id")
        db_order = db.query(OrderHeader).filter(
            OrderHeader.external_order_id == order_id,
            OrderHeader.channel_code == "tiktok"
        ).first()
        
        if not db_order:
            missing += 1
            if missing <= 3:
                print(f"[MISSING] {order_id}")
        else:
            # Check date
            bkk_date = db_order.order_datetime.astimezone(TZ).date()
            if str(bkk_date) != "2026-01-09":
                wrong_date += 1
                if wrong_date <= 3:
                    print(f"[WRONG DATE] {order_id} is {bkk_date}")
            else:
                correct += 1
                
    print(f"\nResult: Missing={missing}, WrongDate={wrong_date}, Correct={correct}")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
