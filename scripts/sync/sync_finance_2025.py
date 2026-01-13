import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services.finance_sync_service import FinanceSyncService

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

async def main():
    db = SessionLocal()
    try:
        service = FinanceSyncService(db)
        
        # Get TikTok Config
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform == 'tiktok'
        ).all()
        
        # Sync 2025 (Jan 1 to Dec 31)
        # Note: TikTok API might be slow for a full year, but we will try.
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        tasks = []
        for config in configs:
            print(f"Syncing Finance for {config.platform} - {config.shop_name} ({start_date.date()} to {end_date.date()})...")
            # We treat each config as a task
            tasks.append(service.sync_platform_finance(
                config=config, 
                time_from=start_date,
                time_to=end_date
            ))
            
        # Run concurrent
        await asyncio.gather(*tasks)
        
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting TikTok Finance Sync for 2025...")
    asyncio.run(main())
