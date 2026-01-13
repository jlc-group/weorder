
import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.services import integration_service
from app.models.integration import PlatformConfig

async def debug_shopee_list():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'shopee', PlatformConfig.is_active == True).first()
        if not config:
            print("No active Shopee config found.")
            return

        client = integration_service.get_client_for_config(config)
        
        # Test range: Jan 2025
        time_from = datetime(2025, 1, 1)
        time_to = datetime(2025, 2, 1)
        
        print(f"Fetching Escrow List for {config.shop_name} ({time_from} - {time_to})...")
        resp = await client.get_escrow_list(time_from, time_to, page_size=1, page_no=1)
        
        if resp:
            print("Response Keys:", resp.keys())
            items = resp.get("escrow_list", [])
            if items:
                print(f"Found {len(items)} items.")
                first_item = items[0]
                print("First Item Keys:", first_item.keys())
                print("First Item:", json.dumps(first_item, indent=2))
            else:
                print("No items in list.")
        else:
            print("Empty response.")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_shopee_list())
