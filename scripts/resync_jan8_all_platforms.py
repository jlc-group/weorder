#!/usr/bin/env python3
"""
Re-sync orders for January 8, 2026 from all platforms.
Uses async properly and counts API results.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.services.sync_service import OrderSyncService

TZ = ZoneInfo("Asia/Bangkok")

async def sync_platform(db, platform: str, start_date: datetime, end_date: datetime):
    """Sync a single platform"""
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == platform,
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        return {"platform": platform, "status": "NO_CONFIG", "synced": 0}
    
    try:
        service = OrderSyncService(db)
        result = await service.sync_platform_orders(
            config=config,
            time_from=start_date,
            time_to=end_date
        )
        return {"platform": platform, "status": "SUCCESS", **result}
    except Exception as e:
        return {"platform": platform, "status": "ERROR", "error": str(e)}

async def main():
    db = SessionLocal()
    
    # Jan 8, 2026 - Full day in UTC (API expects UTC)
    # Bangkok 00:00 = UTC 17:00 (prev day)
    start_date = datetime(2026, 1, 7, 17, 0, 0)  # Jan 8 00:00 Bangkok = Jan 7 17:00 UTC
    end_date = datetime(2026, 1, 8, 16, 59, 59)   # Jan 8 23:59 Bangkok = Jan 8 16:59 UTC
    
    print(f"=== Re-syncing orders for Jan 8, 2026 ===")
    print(f"UTC range: {start_date} to {end_date}")
    print("")
    
    platforms = ["shopee", "tiktok", "lazada"]
    
    for platform in platforms:
        print(f"\n--- {platform.upper()} ---")
        result = await sync_platform(db, platform, start_date, end_date)
        print(f"  Result: {result}")
    
    db.close()
    print("\n=== SYNC COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
