#!/usr/bin/env python3
"""
Quick Monthly Sync Helper
รันทีละเดือนเพื่อป้องกัน timeout และ IDE crash
"""

import subprocess
import sys
from datetime import datetime

def run_month(year: int, month: int, platform: str = None):
    """Run sync for a specific month"""
    
    cmd = [
        sys.executable, 
        "scripts/sync/sync_historical_efficient.py",
        "--year", str(year),
        "--month", str(month)
    ]
    
    if platform:
        cmd.extend(["--platform", platform])
    
    print(f"\n{'='*50}")
    print(f"🚀 Syncing {year}/{month:02d}" + (f" for {platform}" if platform else ""))
    print(f"{'='*50}\n")
    
    result = subprocess.run(cmd, cwd="/Users/chanack/Documents/Weproject/GitHub/App/weorder")
    return result.returncode == 0


def run_all_months(start_year=2025, start_month=1, end_year=2026, end_month=1, platform=None):
    """Run sync for all months in range"""
    
    year = start_year
    month = start_month
    
    success_count = 0
    fail_count = 0
    
    while (year < end_year) or (year == end_year and month <= end_month):
        success = run_month(year, month, platform)
        
        if success:
            success_count += 1
            print(f"✅ {year}/{month:02d} completed successfully")
        else:
            fail_count += 1
            print(f"❌ {year}/{month:02d} failed")
        
        # Next month
        month += 1
        if month > 12:
            month = 1
            year += 1
    
    print(f"\n{'='*50}")
    print(f"📊 SUMMARY: {success_count} months succeeded, {fail_count} months failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monthly Sync Helper")
    parser.add_argument("--platform", "-p", help="Sync only specific platform")
    parser.add_argument("--start-year", type=int, default=2025)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--end-month", type=int, default=1)
    parser.add_argument("--single-month", "-m", type=int, help="Run only this month")
    parser.add_argument("--single-year", "-y", type=int, help="Year for single month")
    
    args = parser.parse_args()
    
    if args.single_month:
        year = args.single_year or datetime.now().year
        run_month(year, args.single_month, args.platform)
    else:
        run_all_months(
            start_year=args.start_year,
            start_month=args.start_month,
            end_year=args.end_year,
            end_month=args.end_month,
            platform=args.platform
        )
