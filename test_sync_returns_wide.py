#!/usr/bin/env python3
"""
Test sync_returns with wider range and pagination fix
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
from app.services.sync_service import OrderSyncService
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader

async def test_sync_returns_wide():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok', 
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("No active TikTok config found")
            return

        print(f"Testing sync_returns for {config.shop_name} (last 90 days)...")
        
        service = OrderSyncService(db)
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=90)
        
        stats = await service.sync_returns(config, time_from, time_to)
        print(f"Sync Returns Results: {stats}")
        
        # Count all RETURNED orders
        returned = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_normalized == 'RETURNED'
        ).count()
        print(f"Total TikTok RETURNED orders now: {returned}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync_returns_wide())
