import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.services import integration_service
from app.services.sync_service import OrderSyncService
from app.models.integration import PlatformConfig

async def sync_90_days():
    db = SessionLocal()
    try:
        # Get active configs
        configs = db.query(PlatformConfig).filter(PlatformConfig.is_active == True).all()
        
        sync_service = OrderSyncService(db)
        
        # 90 days back from NOW
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        print(f"Starting 90-Day Sync: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        for config in configs:
            if not config.access_token:
                print(f"Skipping {config.platform} (No Token)")
                continue

            print(f"\n--- Syncing {config.platform} ({config.shop_name}) ---")
            
            try:
                # Refresh Token if needed
                # client = integration_service.get_client_for_config(config) 
                # OrderSyncService handles client creation internally usually.
                
                # Run Sync
                stats = await sync_service.sync_platform_orders(
                    config=config,
                    time_from=start_date,
                    time_to=end_date
                )
                print(f"Result: {stats}")
                
            except Exception as e:
                print(f"Error syncing {config.platform}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_90_days())
