"""
TikTok Finance Sync - Dedicated Script
Syncs TikTok Statements and Transactions for all active TikTok shops.
Period: Jan 2025 to Now
"""
import asyncio
import sys
import os
import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# Ensure unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 60, flush=True)
print("🎵 TIKTOK FINANCE SYNC - Starting...", flush=True)
print("=" * 60, flush=True)

sys.path.append(os.getcwd())

# Disable SQL logging BEFORE import
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

print("Importing modules...", flush=True)

from app.services.finance_sync_service import FinanceSyncService
from app.core.database import SessionLocal, engine
from app.models.integration import PlatformConfig

# Suppress noisy logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

engine.echo = False

print("Modules loaded.", flush=True)

async def sync_tiktok_finance():
    print("=" * 60)
    print("🎵 TIKTOK FINANCE SYNC")
    print("=" * 60)
    
    db = SessionLocal()
    service = FinanceSyncService(db)
    
    # Date range: Jan 2025 to Now
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    print(f"📅 Period: {start_date.date()} to {end_date.date()}")
    
    try:
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform == "tiktok"
        ).all()
        
        if not configs:
            print("\n⚠️ No active TikTok config found!")
            return
        
        print(f"\n📋 Found {len(configs)} TikTok shop(s)")
        
        for config in configs:
            print(f"\n{'='*40}")
            print(f"🏪 Syncing: {config.shop_name}")
            print(f"{'='*40}")
            
            # Sync in monthly chunks for better progress tracking
            current = start_date
            total_stats = {"fetched": 0, "created": 0, "errors": 0}
            month_count = 0
            
            while current < end_date:
                chunk_end = min(current + relativedelta(months=1), end_date)
                month_count += 1
                print(f"\n  📆 Month {month_count}: {current.date()} -> {chunk_end.date()}...", flush=True)
                
                try:
                    stats = await service.sync_platform_finance(
                        config=config,
                        time_from=current,
                        time_to=chunk_end
                    )
                    total_stats["fetched"] += stats.get("fetched", 0)
                    total_stats["created"] += stats.get("created", 0)
                    total_stats["errors"] += stats.get("errors", 0)
                    print(f"     ✓ Fetched: {stats.get('fetched', 0)}, Created: {stats.get('created', 0)}")
                except Exception as e:
                    print(f"     ✗ Error: {e}")
                    total_stats["errors"] += 1
                
                current = chunk_end
            
            print(f"\n✅ {config.shop_name} Complete:")
            print(f"   Total Fetched: {total_stats['fetched']}")
            print(f"   Total Created: {total_stats['created']}")
            print(f"   Errors: {total_stats['errors']}")
                
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("🎵 TIKTOK FINANCE SYNC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(sync_tiktok_finance())
