
import asyncio
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.services.sync_service import OrderSyncService
from app.models.integration import PlatformConfig

async def catch_up():
    db = SessionLocal()
    service = OrderSyncService(db)
    
    # Sync last 48 hours
    time_from = datetime.utcnow() - timedelta(hours=48)
    
    configs = db.query(PlatformConfig).filter(PlatformConfig.is_active == True).all()
    
    print(f"Starting catch-up sync from {time_from} for {len(configs)} shops")
    
    for config in configs:
        print(f"Syncing {config.platform}/{config.shop_name}...")
        try:
            stats = await service.sync_platform_orders(config, time_from=time_from)
            print(f"Result: {stats}")
        except Exception as e:
            print(f"Failed to sync {config.platform}: {e}")
            
    db.close()

if __name__ == "__main__":
    asyncio.run(catch_up())
