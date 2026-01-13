import sys
import os
import asyncio
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import sync_service

async def run_sync():
    db = SessionLocal()
    try:
        # Get TikTok config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "tiktok").first()
        if not config:
            print("No TikTok config found")
            return

        print(f"Starting sync for {config.shop_name}...")
        
        # Sync December 2025
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2026, 1, 1)
        
        service = sync_service.OrderSyncService(db)
        stats = await service.sync_platform_orders(config, time_from=start_date, time_to=end_date)
        
        print("\nSync Completed!")
        print(f"Fetched: {stats['fetched']}")
        print(f"Created: {stats['created']}")
        print(f"Updated: {stats['updated']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_sync())
