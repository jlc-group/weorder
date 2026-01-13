"""
Complete Finance Sync - All Platforms, Full Year 2025 + Jan 2026
Run overnight to populate full financial data.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

sys.path.append(os.getcwd())

from app.services.finance_sync_service import FinanceSyncService
from app.core.database import SessionLocal, engine
from app.models.integration import PlatformConfig

# Suppress noisy logs
logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

engine.echo = False

async def sync_all_finance():
    print("=" * 60)
    print("COMPLETE FINANCE SYNC - ALL PLATFORMS")
    print("=" * 60)
    
    db = SessionLocal()
    service = FinanceSyncService(db)
    
    # Date range: Jan 2025 to Now
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    platforms = ['shopee', 'tiktok']  # Lazada not yet implemented
    
    try:
        for platform in platforms:
            configs = db.query(PlatformConfig).filter(
                PlatformConfig.is_active == True,
                PlatformConfig.platform == platform
            ).all()
            
            if not configs:
                print(f"\n⚠️ {platform.upper()}: No active config, skipping.")
                continue
            
            for config in configs:
                print(f"\n{'='*40}")
                print(f"Syncing {platform.upper()} - {config.shop_name}")
                print(f"Range: {start_date.date()} to {end_date.date()}")
                print(f"{'='*40}")
                
                # Sync in monthly chunks
                current = start_date
                total_stats = {"fetched": 0, "created": 0, "errors": 0}
                
                while current < end_date:
                    chunk_end = min(current + relativedelta(months=1), end_date)
                    print(f"  Batch: {current.date()} -> {chunk_end.date()}...", end=" ", flush=True)
                    
                    try:
                        stats = await service.sync_platform_finance(
                            config=config,
                            time_from=current,
                            time_to=chunk_end
                        )
                        total_stats["fetched"] += stats.get("fetched", 0)
                        total_stats["created"] += stats.get("created", 0)
                        total_stats["errors"] += stats.get("errors", 0)
                        print(f"✓ {stats}")
                    except Exception as e:
                        print(f"✗ Error: {e}")
                        total_stats["errors"] += 1
                    
                    current = chunk_end
                
                print(f"\n✅ {platform.upper()} Complete: {total_stats}")
                
    except Exception as e:
        print(f"Fatal Error: {e}")
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("ALL FINANCE SYNC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(sync_all_finance())
