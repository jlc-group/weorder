
import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.getcwd())

from app.services.sync_service import OrderSyncService
from app.core.database import SessionLocal, engine
from app.models.integration import PlatformConfig

engine.echo = False

async def sync_missing_months():
    print("=== Syncing Missing TikTok Oct-Nov 2025 ===")
    db = SessionLocal()
    service = OrderSyncService(db)
    
    # Oct 2025 and Nov 2025
    ranges = [
        (datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 11, 1, tzinfo=timezone.utc), "Oct 2025"),
        (datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 12, 1, tzinfo=timezone.utc), "Nov 2025"),
    ]
    
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("No TikTok config found!")
            return
        
        for start, end, label in ranges:
            print(f"\n--- {label}: {start.date()} to {end.date()} ---")
            stats = await service.sync_platform_orders(
                config=config,
                time_from=start,
                time_to=end
            )
            print(f"Result: {stats}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
    
    print("\n=== Done ===")

if __name__ == "__main__":
    asyncio.run(sync_missing_months())
