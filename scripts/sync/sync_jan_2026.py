
import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.sync_service import OrderSyncService
from app.core import settings
from app.core.database import SessionLocal, engine

# Configure Logging (Silent Mode)
logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Force disable SQL echo
engine.echo = False

async def sync_jan_2026():
    print("Starting targeted sync for Jan 2026...")
    db = SessionLocal()
    service = OrderSyncService(db)
    
    # Time range: Jan 1, 2026 to Now
    start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    try:
        from app.models.integration import PlatformConfig
        from app.services import integration_service
        
        # Get all active configs
        configs = db.query(PlatformConfig).filter(PlatformConfig.is_active == True).all()
        
        for config in configs:
            if config.platform in ['tiktok', 'lazada', 'shopee']:
                print(f"Syncing {config.platform} ({config.shop_name})...")
                try:
                    await service.sync_platform_orders(
                        config=config,
                        time_from=start_date,
                        time_to=end_date
                    )
                    print(f"{config.platform} Sync Complete.")
                except Exception as e:
                    print(f"Error syncing {config.platform}: {e}")
        
    except Exception as e:
        print(f"Error during overall sync: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_jan_2026())
