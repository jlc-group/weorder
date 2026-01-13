#!/usr/bin/env python3
"""
Compare TikTok API order counts vs Database counts for Jan 1-10.
Identifies discrepancies between what TikTok returns and what we stored.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader
from app.services import integration_service
from sqlalchemy import func, text

TZ = ZoneInfo("Asia/Bangkok")

async def count_api_orders(client, day: int):
    """Count orders from TikTok API for a specific day"""
    # Convert Bangkok date to UTC timestamps
    start_utc = datetime(2026, 1, day, 0, 0, 0, tzinfo=TZ).astimezone(timezone.utc)
    end_utc = datetime(2026, 1, day, 23, 59, 59, tzinfo=TZ).astimezone(timezone.utc)
    
    total = 0
    cursor = None
    has_more = True
    
    while has_more:
        result = await client.get_orders(
            time_from=start_utc,
            time_to=end_utc,
            cursor=cursor,
            page_size=100
        )
        orders = result.get("orders", [])
        total += len(orders)
        cursor = result.get("next_cursor")
        has_more = result.get("has_more", False) and cursor
    
    return total

def count_db_orders(db, day: int):
    """Count orders in DB for a specific day"""
    query = text(f'''
        SELECT COUNT(*) FROM order_header 
        WHERE channel_code = 'tiktok'
        AND order_datetime >= '2026-01-{day:02d} 00:00:00+07:00'
        AND order_datetime < '2026-01-{day+1:02d} 00:00:00+07:00'
    ''')
    result = db.execute(query).fetchone()
    return result[0]

async def main():
    db = SessionLocal()
    
    # Get TikTok config and client
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == "tiktok",
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        print("ERROR: No active TikTok config")
        return
    
    client = integration_service.get_client_for_config(config)
    
    print("=== TikTok API vs Database Comparison (Jan 1-10, 2026) ===")
    print("")
    print("| วันที่ | TikTok API | Database | ผลต่าง | สถานะ |")
    print("|--------|------------|----------|--------|-------|")
    
    total_api = 0
    total_db = 0
    
    for day in range(1, 11):
        api_count = await count_api_orders(client, day)
        db_count = count_db_orders(db, day)
        diff = api_count - db_count
        
        total_api += api_count
        total_db += db_count
        
        if diff > 100:
            status = "⚠️ ขาดเยอะ"
        elif diff > 0:
            status = "⚡ ขาดบ้าง"
        elif diff < 0:
            status = "❓ เกิน?"
        else:
            status = "✅"
        
        print(f"| {day:02d} ม.ค. | {api_count:,} | {db_count:,} | {diff:+,} | {status} |")
    
    print("")
    print(f"รวม: API={total_api:,} | DB={total_db:,} | ผลต่าง={total_api-total_db:+,}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
