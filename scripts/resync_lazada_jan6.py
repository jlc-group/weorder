import sys
import os
import asyncio
from datetime import datetime, timedelta
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.services.sync_service import OrderSyncService

async def resync_lazada():
    print("--- Re-syncing Lazada for Jan 6th Period ---")
    
    db = SessionLocal()
    
    # 1. Get Config
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    if not config:
        print("Error: Lazada is not configured/active.")
        return

    # 2. Use Sync Service
    service = OrderSyncService(db)
    
    # Sync window: Jan 5 to Jan 8
    # Using UTC conversion or just naive datetime? Service expects datetime.
    # sync_platform_orders handles time conversion usually, 
    # but passed params are treated as 'created_after' / 'created_before' usually.
    # Let's give a slightly wider range.
    start_date = datetime(2026, 1, 5)
    end_date = datetime(2026, 1, 8)
    
    print(f"Syncing from {start_date} to {end_date}...")
    
    try:
        stats = await service.sync_platform_orders(config, start_date, end_date)
        print("\n✅ Lazada Re-sync Complete.")
        print(f"Stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(resync_lazada())
