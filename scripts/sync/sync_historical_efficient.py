#!/usr/bin/env python3
"""
Efficient Historical Sync Script
- Syncs data month by month with progress tracking
- Saves progress to resume if interrupted
- Writes logs to file instead of stdout (prevents IDE crash)
"""

import asyncio
import json
import logging
import sys
import os
sys.path.append(os.getcwd())
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core import get_db
from app.services import integration_service, sync_service, finance_sync_service
from app.models.integration import PlatformConfig

# ============ CONFIGURATION ============
CHUNK_DAYS = 15  # Days per sync chunk
START_YEAR = 2025
START_MONTH = 1
END_YEAR = 2026
END_MONTH = 1
PROGRESS_FILE = Path("sync_progress.json")
LOG_FILE = Path("sync_historical.log")
# ========================================

# Setup file-based logging to prevent IDE crash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_progress() -> dict:
    """Load sync progress from file"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"completed_ranges": [], "stats": {}}


def save_progress(progress: dict):
    """Save sync progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2, default=str)


def is_range_completed(progress: dict, platform: str, start: datetime, end: datetime) -> bool:
    """Check if a date range has already been synced"""
    key = f"{platform}:{start.date()}:{end.date()}"
    return key in progress.get("completed_ranges", [])


def mark_range_completed(progress: dict, platform: str, start: datetime, end: datetime):
    """Mark a date range as completed"""
    key = f"{platform}:{start.date()}:{end.date()}"
    if "completed_ranges" not in progress:
        progress["completed_ranges"] = []
    progress["completed_ranges"].append(key)
    save_progress(progress)


async def sync_platform_chunk(
    service: sync_service.OrderSyncService,
    config: PlatformConfig,
    start_date: datetime,
    end_date: datetime,
    progress: dict,
    force: bool = False
) -> dict:
    """Sync a single chunk of data for a platform"""
    
    if not force and is_range_completed(progress, config.platform, start_date, end_date):
        logger.info(f"  ⏭️  Skipping {start_date.date()} to {end_date.date()} (already completed)")
        return {"fetched": 0, "created": 0, "updated": 0, "skipped": 1}
    
    logger.info(f"  📥 Syncing {start_date.date()} to {end_date.date()}...")
    
    try:
        stats = await service.sync_platform_orders(
            config,
            time_from=start_date,
            time_to=end_date
        )
        
        # Mark as completed
        mark_range_completed(progress, config.platform, start_date, end_date)
        
        logger.info(f"  ✅ Done: fetched={stats.get('fetched', 0)}, created={stats.get('created', 0)}, updated={stats.get('updated', 0)}")
        
        return stats
        
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return {"fetched": 0, "created": 0, "updated": 0, "errors": 1}


async def sync_platform_month(
    service: sync_service.OrderSyncService,
    finance_service: finance_sync_service.FinanceSyncService,
    config: PlatformConfig,
    year: int,
    month: int,
    progress: dict
) -> dict:
    """Sync one month of data for a platform, chunked by CHUNK_DAYS"""
    
    # Calculate month boundaries
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    logger.info(f"\n📅 {config.platform} - {year}/{month:02d} ({month_start.date()} to {month_end.date()})")
    
    month_stats = {"fetched": 0, "created": 0, "updated": 0, "errors": 0, "skipped": 0}
    
    current_start = month_start
    while current_start < month_end:
        current_end = min(current_start + timedelta(days=CHUNK_DAYS), month_end)
        
        chunk_stats = await sync_platform_chunk(
            service, config, current_start, current_end, progress, force=args.force
        )
        
        # Sync Finance
        try:
            logger.info(f"  💰 Syncing Finance {current_start.date()} to {current_end.date()}...")
            f_stats = await finance_service.sync_platform_finance(config, current_start, current_end)
            logger.info(f"     -> Finance: {f_stats}")
        except Exception as e:
            logger.error(f"     -> Finance Error: {e}")

        # Sync Returns (TikTok specific)
        try:
           if config.platform == "tiktok" and False: # Disabled temporarily due to API 404
               logger.info(f"  ↩️ Syncing Returns {current_start.date()} to {current_end.date()}...")
               r_stats = await service.sync_returns(config, current_start, current_end)
               if r_stats.get("updated", 0) > 0:
                   logger.info(f"     -> Returns Updated: {r_stats['updated']}")
                   chunk_stats['updated'] += r_stats['updated']
        except Exception as e:
            logger.error(f"     -> Returns Sync Error: {e}")

        # Accumulate stats
        
        # Accumulate stats
        for key in month_stats:
            month_stats[key] += chunk_stats.get(key, 0)
        
        current_start = current_end + timedelta(seconds=1)
        
        # Rate limit protection
        await asyncio.sleep(0.5)
    
    return month_stats


async def sync_platform_full(config: PlatformConfig, progress: dict) -> dict:
    """Sync all historical data for a platform"""
    
    db = next(get_db())
    service = sync_service.OrderSyncService(db)
    finance_service = finance_sync_service.FinanceSyncService(db)
    
    total_stats = {"fetched": 0, "created": 0, "updated": 0, "errors": 0, "skipped": 0}
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🏪 Starting sync for: {config.platform} ({config.shop_name})")
    logger.info(f"{'='*60}")
    
    try:
        # Iterate through months
        year = START_YEAR
        month = START_MONTH
        
        while (year < END_YEAR) or (year == END_YEAR and month <= END_MONTH):
            month_stats = await sync_platform_month(service, finance_service, config, year, month, progress)
            
            # Accumulate stats
            for key in total_stats:
                total_stats[key] += month_stats.get(key, 0)
            
            # Next month
            month += 1
            if month > 12:
                month = 1
                year += 1
        
        logger.info(f"\n✅ Completed {config.platform}")
        logger.info(f"   Total: fetched={total_stats['fetched']}, created={total_stats['created']}, updated={total_stats['updated']}")
        
    except Exception as e:
        logger.error(f"❌ Fatal error for {config.platform}: {e}")
        total_stats["errors"] += 1
    finally:
        db.close()
    
    return total_stats


async def main(platform_filter: Optional[str] = None):
    """Main entry point"""
    
    logger.info("="*60)
    logger.info("🚀 EFFICIENT HISTORICAL SYNC")
    logger.info(f"   Period: {START_YEAR}/{START_MONTH:02d} to {END_YEAR}/{END_MONTH:02d}")
    logger.info(f"   Chunk size: {CHUNK_DAYS} days")
    logger.info(f"   Progress file: {PROGRESS_FILE}")
    logger.info(f"   Log file: {LOG_FILE}")
    logger.info("="*60)
    
    # Load progress
    progress = load_progress()
    completed_count = len(progress.get("completed_ranges", []))
    if completed_count > 0:
        logger.info(f"📂 Resuming from previous run ({completed_count} chunks already completed)")
    
    # Get platforms
    db = next(get_db())
    try:
        configs = integration_service.get_platform_configs(db, is_active=True)
        active_configs = [c for c in configs if c.sync_enabled]
        
        # Filter if specified
        if platform_filter:
            active_configs = [c for c in active_configs if platform_filter.lower() in c.platform.lower()]
        
        logger.info(f"\n📋 Found {len(active_configs)} platform(s) to sync:")
        for c in active_configs:
            logger.info(f"   - {c.platform} ({c.shop_name})")
        
    finally:
        db.close()
    
    # Sync each platform
    all_results = {}
    for config in active_configs:
        result = await sync_platform_full(config, progress)
        all_results[config.platform] = result
        
        # Save platform stats
        if "stats" not in progress:
            progress["stats"] = {}
        progress["stats"][config.platform] = result
        save_progress(progress)
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("📊 FINAL SUMMARY")
    logger.info("="*60)
    
    total_all = {"fetched": 0, "created": 0, "updated": 0, "errors": 0}
    for platform, stats in all_results.items():
        logger.info(f"  {platform}:")
        logger.info(f"    Fetched: {stats['fetched']}, Created: {stats['created']}, Updated: {stats['updated']}, Errors: {stats['errors']}")
        for key in total_all:
            total_all[key] += stats.get(key, 0)
    
    logger.info(f"\n  TOTAL:")
    logger.info(f"    Fetched: {total_all['fetched']}, Created: {total_all['created']}, Updated: {total_all['updated']}, Errors: {total_all['errors']}")
    logger.info("\n✅ Sync complete!")


def run_sync(platform: Optional[str] = None, reset_progress: bool = False):
    """
    Run the sync process
    
    Args:
        platform: Optional platform filter (e.g., 'shopee', 'tiktok')
        reset_progress: If True, delete progress file and start fresh
    """
    if reset_progress and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print(f"🗑️  Deleted progress file: {PROGRESS_FILE}")
    
    asyncio.run(main(platform))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Efficient Historical Sync")
    parser.add_argument("--platform", "-p", help="Sync only specific platform (e.g., shopee, tiktok)")
    parser.add_argument("--reset", "-r", action="store_true", help="Reset progress and start fresh")
    parser.add_argument("--month", "-m", type=int, help="Sync only specific month (1-12)")
    parser.add_argument("--force", action="store_true", help="Force sync (ignore completed jobs)")
    parser.add_argument("--year", "-y", type=int, help="Sync only specific year")
    
    args = parser.parse_args()
    
    # Override global config if specific month/year provided
    if args.month:
        START_MONTH = args.month
        END_MONTH = args.month
    if args.year:
        START_YEAR = args.year
        END_YEAR = args.year
    
    run_sync(platform=args.platform, reset_progress=args.reset)
