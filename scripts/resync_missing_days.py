#!/usr/bin/env python3
"""
Re-sync orders for missing days (Jan 8 and 10) from all platforms.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader
from app.services.sync_service import OrderSyncService
from sqlalchemy import func, cast, Date

TZ = ZoneInfo("Asia/Bangkok")

async def sync_platform(db, platform: str, start_date: datetime, end_date: datetime):
    """Sync a single platform"""
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == platform,
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        return {"platform": platform, "status": "NO_CONFIG"}
    
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

def get_counts(db, date_str):
    """Get order counts for a specific date"""
    results = db.query(OrderHeader.channel_code, func.count(OrderHeader.id)).filter(
        cast(OrderHeader.order_datetime, Date) == date_str
    ).group_by(OrderHeader.channel_code).all()
    return dict(results)

async def main():
    db = SessionLocal()
    
    # Days to sync: Jan 8 and Jan 10
    days_to_sync = [8, 10]
    platforms = ["shopee", "tiktok", "lazada"]
    
    for day in days_to_sync:
        print(f"\n{'='*50}")
        print(f"=== Re-syncing Jan {day}, 2026 ===")
        print(f"{'='*50}")
        
        # Record BEFORE counts
        date_str = f"2026-01-{day:02d}"
        before = get_counts(db, date_str)
        print(f"BEFORE: {before}")
        
        # UTC time range for Bangkok date
        # Bangkok 00:00 = UTC 17:00 (prev day)
        start_date = datetime(2026, 1, day-1, 17, 0, 0)
        end_date = datetime(2026, 1, day, 16, 59, 59)
        
        print(f"UTC range: {start_date} to {end_date}")
        
        for platform in platforms:
            print(f"\n--- {platform.upper()} ---")
            result = await sync_platform(db, platform, start_date, end_date)
            if result.get("status") == "SUCCESS":
                print(f"  Fetched: {result.get('fetched', 0)}, Created: {result.get('created', 0)}, Updated: {result.get('updated', 0)}")
            else:
                print(f"  Result: {result}")
        
        # Record AFTER counts
        after = get_counts(db, date_str)
        print(f"\nAFTER: {after}")
        
        # Calculate difference
        print("\nDIFFERENCE:")
        for ch in ["shopee", "tiktok", "lazada"]:
            diff = after.get(ch, 0) - before.get(ch, 0)
            if diff > 0:
                print(f"  {ch}: +{diff}")
    
    db.close()
    print("\n=== ALL SYNC COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
