#!/usr/bin/env python3
"""
Re-sync Lazada Orders for Dec 2025 (Backlog Recovery).
Target: Dec 25 - Dec 31, 2025.
"""
import sys
import os
import asyncio
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.sync_service import OrderSyncService
from app.core import SessionLocal
from app.models.integration import PlatformConfig

async def resync_lazada_dec():
    print("=== Starting Lazada Re-sync for Dec 25-31, 2025 ===")
    
    db = SessionLocal()
    
    # 1. Get Credentials
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == 'lazada',
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        print("Error: Active Lazada configuration not found.")
        return

    # 2. Define Range
    start_date = datetime(2025, 12, 25)
    end_date = datetime(2025, 12, 31, 23, 59, 59)
    
    print(f"Syncing Lazada from {start_date} to {end_date}...")
    
    try:
        # 3. Call Sync Service
        service = OrderSyncService(db)
        
        result = await service.sync_platform_orders(
            config=config,
            time_from=start_date,
            time_to=end_date
        )
        
        print("\n=== Sync Result ===")
        print(f"Total Processed: {result.get('total_processed', 0)}")
        print(f"New Orders: {result.get('new_orders', 0)}")
        print(f"Updated Orders: {result.get('updated_orders', 0)}")
        print(f"Errors: {result.get('errors', 0)}")
        
    except Exception as e:
        print(f"Sync Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(resync_lazada_dec())
