#!/usr/bin/env python3
"""
Audit TikTok IDs: Fetch Jan 8 orders from API and check each one in DB.
Goal: Find out where the missing 874 orders are hiding.
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
from sqlalchemy import text

TZ = ZoneInfo("Asia/Bangkok")

async def main():
    db = SessionLocal()
    
    # Get TikTok config
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == "tiktok",
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        print("No TikTok config")
        return

    client = integration_service.get_client_for_config(config)
    
    # Jan 8 UTC range
    start_utc = datetime(2026, 1, 7, 17, 0, 0, tzinfo=timezone.utc)
    end_utc = datetime(2026, 1, 8, 16, 59, 59, tzinfo=timezone.utc)
    
    print("Fetching Jan 8 orders from TikTok API...")
    
    # Just fetch first 300 to get a sample of "missing" ones
    # (Since 874 are missing out of 2364, we have ~37% chance to find one per order)
    
    all_api_orders = []
    cursor = None
    has_more = True
    page = 0
    
    while has_more and len(all_api_orders) < 500:
        result = await client.get_orders(
            time_from=start_utc,
            time_to=end_utc,
            cursor=cursor,
            page_size=100
        )
        orders = result.get("orders", [])
        all_api_orders.extend(orders)
        cursor = result.get("next_cursor")
        has_more = result.get("has_more", False) and cursor
        page += 1
        print(f"Fetched {len(all_api_orders)} orders...")

    print(f"Analyzing {len(all_api_orders)} orders against DB...")
    
    found_count = 0
    missing_count = 0
    found_wrong_date = 0
    
    print("\n--- Discrepancy Sample ---")
    
    for api_order in all_api_orders:
        order_id = api_order.get("id")
        # Check DB
        db_order = db.query(OrderHeader).filter(
            OrderHeader.external_order_id == order_id,
            OrderHeader.channel_code == "tiktok"
        ).first()
        
        if not db_order:
            missing_count += 1
            if missing_count <= 5:
                print(f"[MISSING] {order_id} - Not found in DB")
        else:
            # Check date
            db_date = db_order.order_datetime
            # Convert DB date to Bangkok date string for comparison
            # Jan 8 Bangkok is target
            if not db_date:
                 print(f"[FOUND-NULL] {order_id} date is NULL")
                 continue

            bkk_date = db_date.astimezone(TZ).date()
            if str(bkk_date) != "2026-01-08":
                found_wrong_date += 1
                if found_wrong_date <= 5:
                    print(f"[FOUND-WRONG-DATE] {order_id} is {bkk_date} (Expected 2026-01-08)")
            else:
                found_count += 1

    print("\n=== Audit Result (Sample size: {}) ===".format(len(all_api_orders)))
    print(f"Found Correct Date: {found_count}")
    print(f"Found Wrong Date:   {found_wrong_date}")
    print(f"Missing Completely: {missing_count}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
