import sys
import os
import asyncio
from datetime import datetime, timedelta
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.services.sync_service import OrderSyncService

async def force_shopee_sync():
    print("--- Forcing Shopee Sync ---")
    
    db = SessionLocal()
    
    # 1. Get Config
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'shopee', PlatformConfig.is_active == True).first()
    if not config:
        print("Error: Shopee is not configured/active.")
        return

    # 2. Use Sync Service
    service = OrderSyncService(db)
    
    # Sync window: Last 24 hours to catch up
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=24)
    
    print(f"Syncing from {start_date} to {end_date}...")
    
    try:
        stats = await service.sync_platform_orders(config, start_date, end_date)
        print("\n✅ Shopee Sync Complete.")
        print(f"Stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(force_shopee_sync())
