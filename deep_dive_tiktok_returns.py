#!/usr/bin/env python3
"""
Deep dive into why TikTok returns are few in DB
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
from app.models.order import OrderHeader
print("Models imported")
from app.services import integration_service
print("Integration service imported")

async def deep_dive_returns():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok', 
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("No active TikTok config found")
            return

        client = integration_service.get_client_for_config(config)
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=60) # Back 60 days to be safe
        
        print(f"Fetching reverse orders from API (last 60 days)...")
        result = await client.get_reverse_orders(time_from, time_to)
        returns = result.get("returns", [])
        print(f"API found {len(returns)} reverse orders.")
        
        print("\nChecking against DB:")
        print(f"{'Order ID':<20} | {'Tiktok Status':<35} | {'DB Status':<15} | {'Exists?'}")
        print("-" * 85)
        
        for r in returns:
            order_id = r.get("order_id")
            tiktok_status = r.get("return_status") or r.get("cancel_status")
            
            order = db.query(OrderHeader).filter(
                OrderHeader.external_order_id == order_id
            ).first()
            
            exists = "YES" if order else "NO"
            db_status = order.status_normalized if order else "N/A"
            
            print(f"{order_id:<20} | {str(tiktok_status):<35} | {db_status:<15} | {exists}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(deep_dive_returns())
