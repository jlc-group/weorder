#!/usr/bin/env python3
"""
Direct test of TikTok get_reverse_orders without database overhead
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

print("Imports starting...")
from app.core.database import SessionLocal
print("Database imported")
from app.models.integration import PlatformConfig
print("Models imported")
from app.services import integration_service
print("Integration service imported")

async def test_get_reverse():
    print("\n=== Testing get_reverse_orders ===")
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok', 
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("No active TikTok config found")
            return
        
        print(f"Config: {config.shop_name}")
        
        client = integration_service.get_client_for_config(config)
        print("Client created")
        
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=30)
        
        print("Calling get_reverse_orders...")
        result = await client.get_reverse_orders(time_from, time_to)
        print(f"Result: {result}")
        
        returns = result.get("returns", [])
        print(f"Found {len(returns)} reverse orders")
        
        for r in returns[:5]:
            print(f"  - {r.get('order_id')} | Status: {r.get('return_status')}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_get_reverse())
