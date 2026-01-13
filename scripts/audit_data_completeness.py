"""
Data Completeness Audit: API vs DB Comparison by Month
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, extract

sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.order import OrderHeader
from app.models.integration import PlatformConfig
from app.services import integration_service

async def get_api_count(client, platform: str, start: datetime, end: datetime) -> int:
    """Get order count from platform API for a date range"""
    try:
        if platform == "tiktok":
            result = await client.get_orders(time_from=start, time_to=end, page_size=1)
            return result.get("total", 0)
        elif platform == "shopee":
            result = await client.get_orders(time_from=start, time_to=end, page_size=1)
            return result.get("total", 0)
        elif platform == "lazada":
            result = await client.get_orders(time_from=start, time_to=end, page_size=1)
            return result.get("total", 0)
    except Exception as e:
        print(f"  [API Error] {platform}: {e}")
        return -1
    return 0

def get_db_count(db, platform: str, year: int, month: int) -> int:
    """Get order count from DB for a specific month"""
    return db.query(func.count(OrderHeader.id)).filter(
        OrderHeader.channel_code == platform,
        extract('year', OrderHeader.order_datetime) == year,
        extract('month', OrderHeader.order_datetime) == month
    ).scalar() or 0

async def run_audit():
    db = SessionLocal()
    
    # Months to check: Jan 2025 to Jan 2026
    months = []
    current = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_limit = datetime(2026, 2, 1, tzinfo=timezone.utc)
    while current < end_limit:
        months.append((current.year, current.month))
        current += relativedelta(months=1)
    
    platforms = ['tiktok', 'shopee', 'lazada']
    
    print("\n" + "="*80)
    print("DATA COMPLETENESS AUDIT: Platform API vs Local Database")
    print("="*80)
    
    for platform in platforms:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == platform,
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print(f"\n⚠️  {platform.upper()}: No active config found, skipping.")
            continue
        
        print(f"\n{'='*30} {platform.upper()} {'='*30}")
        print(f"{'Month':<12} | {'API Count':>10} | {'DB Count':>10} | {'Diff':>10} | {'Status':<10}")
        print("-"*60)
        
        try:
            client = integration_service.get_client_for_config(config)
            
            for year, month in months:
                start = datetime(year, month, 1, tzinfo=timezone.utc)
                end = start + relativedelta(months=1)
                
                api_count = await get_api_count(client, platform, start, end)
                db_count = get_db_count(db, platform, year, month)
                diff = db_count - api_count if api_count >= 0 else "N/A"
                
                if api_count < 0:
                    status = "⚠️ API ERR"
                elif diff == 0:
                    status = "✅ OK"
                elif isinstance(diff, int) and diff < 0:
                    status = f"❌ Missing {abs(diff)}"
                else:
                    status = f"⚠️ Extra {diff}"
                
                month_str = f"{year}-{month:02d}"
                api_str = str(api_count) if api_count >= 0 else "ERROR"
                diff_str = str(diff) if isinstance(diff, int) else diff
                
                print(f"{month_str:<12} | {api_str:>10} | {db_count:>10} | {diff_str:>10} | {status:<10}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "="*80)
    print("Audit Complete")
    print("="*80)
    
    db.close()

if __name__ == "__main__":
    asyncio.run(run_audit())
