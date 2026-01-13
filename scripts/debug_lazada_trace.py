import asyncio
import sys, os
import json
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import PlatformConfig
from app.integrations.lazada import LazadaClient

async def debug_lazada_trace():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "lazada", PlatformConfig.is_active == True).first()
        if not config:
            print("Lazada config not found")
            return

        client = LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
        )

        target_order_id = "1074255913052684" # Known delivered order
        
        print(f"Testing endpoints for order {target_order_id}...")

        # 1. Standard Order Detail
        print("\n--- /order/get ---")
        try:
            order = await client._make_request("/order/get", params={"order_id": target_order_id})
            print(f"Updated At: {order.get('updated_at')}")
            print(f"Statuses: {order.get('statuses')}")
        except Exception as e:
            print(f"Error: {e}")

        # 2. Logistics Trace (Speculative)
        print("\n--- /logistic/order/trace ---")
        try:
            # Note: This endpoint might require package_id or order_id
            params = {
                "order_id": target_order_id,
                "package_id": "FP081213126802230",
                "seller_id": config.shop_id,
                "locale": "th_TH"
            }
            trace = await client._make_request("/logistic/order/trace", params=params)
            print(json.dumps(trace, indent=2))
        except Exception as e:
            print(f"Error: {e}") 
            
        print("\n--- /logistic/package/trace (Speculative) ---")
        try:
           params = {
                "package_id": "FP081213126802230",
                "seller_id": config.shop_id,
                "locale": "th_TH"
            }
           trace = await client._make_request("/logistic/package/trace", params=params)
           print(json.dumps(trace, indent=2))
        except Exception as e:
            print(f"Error: {e}")

        # 3. Get Shipment Providers (might give hints)
        print("\n--- /shipment/providers/get ---")
        try:
            providers = await client._make_request("/shipment/providers/get")
            print(f"Providers count: {len(providers)}")
        except Exception as e:
            print(f"Error: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_lazada_trace())
