#!/usr/bin/env python3
"""
Verify TikTok order count by calling API directly.
Counts how many orders TikTok API returns for Jan 8, 2026.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service

TZ = ZoneInfo("Asia/Bangkok")

async def main():
    db = SessionLocal()
    
    # Get TikTok config
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == "tiktok",
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        print("ERROR: No active TikTok config found")
        return
    
    print(f"Using TikTok config: {config.shop_name} (ID: {config.shop_id})")
    
    # Get TikTok client
    client = integration_service.get_client_for_config(config)
    
    # Jan 8, 2026 - Convert Bangkok time to UTC timestamps
    # Bangkok 00:00 Jan 8 = UTC 17:00 Jan 7
    start_utc = datetime(2026, 1, 7, 17, 0, 0)
    end_utc = datetime(2026, 1, 8, 16, 59, 59)
    
    print(f"\nQuerying TikTok API for orders:")
    print(f"  UTC Start: {start_utc}")
    print(f"  UTC End: {end_utc}")
    print(f"  Bangkok: Jan 8, 2026 00:00 - 23:59")
    print("")
    
    # Call API and count
    total_orders = 0
    cursor = None
    has_more = True
    page = 0
    
    while has_more:
        page += 1
        print(f"Fetching page {page}...", end=" ")
        
        try:
            result = await client.get_orders(
                time_from=start_utc,
                time_to=end_utc,
                cursor=cursor,
                page_size=100
            )
            
            orders = result.get("orders", [])
            total_orders += len(orders)
            cursor = result.get("next_cursor")
            has_more = result.get("has_more", False) and cursor
            
            print(f"Got {len(orders)} orders (Total: {total_orders})")
            
        except Exception as e:
            print(f"ERROR: {e}")
            break
    
    print(f"\n{'='*50}")
    print(f"TIKTOK API RESULT FOR JAN 8, 2026:")
    print(f"Total orders from API: {total_orders}")
    print(f"{'='*50}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
