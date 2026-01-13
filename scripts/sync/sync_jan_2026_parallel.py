
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.getcwd())

from app.services.sync_service import OrderSyncService
from app.core.database import SessionLocal, engine

# Configure Logging (Silent Mode)
logging.basicConfig(level=logging.INFO) # Info to clear stdout
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Force disable SQL echo
engine.echo = False

async def sync_config(config_id, platform, shop_name):
    # New DB session per task
    db = SessionLocal()
    service = OrderSyncService(db)
    
    start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    try:
        from app.models.integration import PlatformConfig
        # Re-fetch config to be attached to session
        config = db.query(PlatformConfig).filter(PlatformConfig.id == config_id).first()
        
        if config:
            print(f"[{platform}] Syncing {shop_name}...")
            await service.sync_platform_orders(
                config=config,
                time_from=start_date,
                time_to=end_date
            )
            print(f"[{platform}] {shop_name} Complete.")
    except Exception as e:
        print(f"[{platform}] Error: {e}")
    finally:
        db.close()

async def sync_parallel():
    print("Starting PARALLEL sync for Jan 2026...")
    db = SessionLocal()
    try:
        from app.models.integration import PlatformConfig
        configs = db.query(PlatformConfig).filter(
            PlatformConfig.is_active == True,
            PlatformConfig.platform.in_(['tiktok', 'lazada', 'shopee'])
        ).all()
        
        tasks = []
        for c in configs:
            # Pass ID to worker to re-fetch
            tasks.append(sync_config(c.id, c.platform, c.shop_name))
            
        print(f"Launched {len(tasks)} parallel sync tasks.")
        await asyncio.gather(*tasks)
        print("All syncs finished.")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_parallel())
