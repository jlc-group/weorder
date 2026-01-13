
import asyncio
import logging
import sys
import os
import json

sys.path.append(os.getcwd())
from app.core import get_db
from app.services import integration_service
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_single_invoice():
    db = next(get_db())
    try:
        # 1. Get Config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs:
            print("No active Shopee config")
            return
        
        config = configs[0]
        client = integration_service.get_client_for_config(config)
        print(f"Checking Shopee Shop: {config.shop_name}")
        
        # 2. Get recent orders
        print("Fetching last 50 Shopee orders...")
        result = db.execute(text("""
            SELECT external_order_id, order_datetime 
            FROM order_header 
            WHERE channel_code = 'shopee' 
            AND order_datetime >= '2025-01-01'
            ORDER BY order_datetime DESC 
            LIMIT 50
        """))
        orders = result.fetchall()
        print(f"Found {len(orders)} orders. Checking for invoice_data...")

        found_invoice = 0
        for i, row in enumerate(orders):
            order_sn = row[0]
            # print(f"[{i+1}/{len(orders)}] Checking {order_sn}...", end='\r')
            
            try:
                data = await client.get_order_detail(order_sn)
                if data and data.get("invoice_data"):
                    print(f"\n✅ FOUND INVOICE DATA: {order_sn}")
                    print(json.dumps(data.get("invoice_data"), indent=2, ensure_ascii=False))
                    found_invoice += 1
                else:
                    # Print a dot for progress every 5 orders
                    if (i + 1) % 5 == 0:
                         print(".", end="", flush=True)

            except Exception as e:
                print(f"x", end="", flush=True)
            
            # Rate limit
            await asyncio.sleep(0.1)

        print(f"\n\n--- Summary ---")
        print(f"Scanned: {len(orders)}")
        print(f"Found Official Invoices: {found_invoice}")

    finally:
        db.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_single_invoice())
