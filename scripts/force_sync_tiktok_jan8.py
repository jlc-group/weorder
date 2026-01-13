#!/usr/bin/env python3
"""
Force sync ALL TikTok orders for Jan 8, 2026.
Fetches orders from API and ensures they are all in the database.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader
from app.services.sync_service import OrderSyncService
from sqlalchemy import func, cast, Date

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
    
    # Record BEFORE count
    before_count = db.query(func.count(OrderHeader.id)).filter(
        OrderHeader.channel_code == "tiktok",
        cast(OrderHeader.order_datetime, Date) == "2026-01-08"
    ).scalar() or 0
    
    print(f"=== Force Sync TikTok Orders for Jan 8, 2026 ===")
    print(f"BEFORE: {before_count} orders in DB")
    print("")
    
    # Jan 8, 2026 - Convert Bangkok time to UTC
    start_utc = datetime(2026, 1, 7, 17, 0, 0)
    end_utc = datetime(2026, 1, 8, 16, 59, 59)
    
    print(f"UTC Range: {start_utc} to {end_utc}")
    print("Starting sync...")
    
    try:
        service = OrderSyncService(db)
        result = await service.sync_platform_orders(
            config=config,
            time_from=start_utc,
            time_to=end_utc
        )
        
        print(f"\nSync Result:")
        print(f"  Fetched: {result.get('fetched', 0)}")
        print(f"  Created: {result.get('created', 0)}")
        print(f"  Updated: {result.get('updated', 0)}")
        print(f"  Skipped: {result.get('skipped', 0)}")
        print(f"  Errors: {result.get('errors', 0)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Record AFTER count
    after_count = db.query(func.count(OrderHeader.id)).filter(
        OrderHeader.channel_code == "tiktok",
        cast(OrderHeader.order_datetime, Date) == "2026-01-08"
    ).scalar() or 0
    
    print(f"\n{'='*50}")
    print(f"BEFORE: {before_count} orders")
    print(f"AFTER: {after_count} orders")
    print(f"ADDED: +{after_count - before_count} orders")
    print(f"{'='*50}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
