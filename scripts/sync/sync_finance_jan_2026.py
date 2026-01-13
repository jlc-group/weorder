
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.getcwd())

from app.services.finance_sync_service import FinanceSyncService
from app.core.database import SessionLocal, engine
from app.models.integration import PlatformConfig

# Configure Logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

async def sync_finance_jan26():
    print("Starting Finance Sync for Jan 2026...")
    db = SessionLocal()
    service = FinanceSyncService(db)
    
    # Time range: Jan 1, 2026 to Now
    start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    try:
        # Get Shopee & TikTok Configs
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform.in_(['shopee', 'tiktok'])
        ).all()
        
        for config in configs:
            print(f"Syncing Finance for {config.platform} - {config.shop_name}...")
            stats = await service.sync_platform_finance(
                config=config,
                time_from=start_date,
                time_to=end_date
            )
            print(f"Stats: {stats}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_finance_jan26())
