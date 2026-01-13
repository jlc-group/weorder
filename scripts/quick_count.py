
import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())
from app.core import get_db
from app.services import integration_service
from sqlalchemy import text

async def check():
    db = next(get_db())
    try:
        # Get config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs: return
        client = integration_service.get_client_for_config(configs[0])
        
        # Get orders
        result = db.execute(text("""
            SELECT external_order_id FROM order_header 
            WHERE channel_code = 'shopee' AND order_datetime >= '2025-01-01'
            ORDER BY order_datetime DESC LIMIT 50
        """))
        orders = result.fetchall()
        
        found = 0
        print(f"Scanning {len(orders)} orders...", end="", flush=True)
        
        for i, row in enumerate(orders):
            try:
                data = await client.get_order_detail(row[0])
                if data and data.get("invoice_data"):
                    found += 1
            except: pass
            if i % 10 == 0: print(".", end="", flush=True)
            await asyncio.sleep(0.05)
            
        print(f"\nRESULT: {found}")
    finally:
        db.close()

if __name__ == "__main__":
    if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())
