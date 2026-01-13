#!/usr/bin/env python3
"""
Test sync_returns directly without full order sync
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

async def test_sync_returns_only():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok', 
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("No active TikTok config found")
            return

        print(f"Testing sync_returns for {config.shop_name}...")
        
        # Check order before
        order_id = "581932196284761716"
        order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
        if order:
            print(f"Before: {order_id} | Status: {order.status_normalized} | Raw: {order.status_raw}")
        
        service = OrderSyncService(db)
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=30)
        
        # Call sync_returns directly
        stats = await service.sync_returns(config, time_from, time_to)
        print(f"Sync Returns Results: {stats}")
        
        # Refresh and check after
        db.expire_all()
        order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
        if order:
            print(f"After: {order_id} | Status: {order.status_normalized} | Raw: {order.status_raw}")
        
        # Count all RETURNED orders
        returned = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_normalized == 'RETURNED'
        ).count()
        print(f"Total TikTok RETURNED orders: {returned}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync_returns_only())
