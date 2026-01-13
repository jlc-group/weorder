import sys
import os
import asyncio
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service

async def debug_tiktok_response():
    db = SessionLocal()
    try:
        # Get TikTok config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "tiktok").first()
        if not config:
            print("No TikTok config found")
            return

        client = integration_service.get_client_for_config(config)
        
        # Manually call _make_request to see raw keys
        # Use a wide enough range to ensure we get > 0 orders
        print("Fetching first page of orders...")
        
        # We need to access the private method or replicate the call parameters?
        # Let's use get_orders but modify it temporarily or just print inside? 
        # Easier: just call the public get_orders and print the result, 
        # BUT get_orders filters the keys.
        
        # So we will access the protected _make_request if possible or copy its logic.
        # Python allows access to protected members.
        
        params = {
            "page_size": 10,
            "sort_field": "create_time",
            "sort_order": "DESC",
        }
        body = {}
        
        # Call _make_request directly
        data = await client._make_request("/search", method="POST", params=params, body=body)
        
        print("\n=== API RESPONSE KEYS ===")
        print(json.dumps(list(data.keys()), indent=2))
        
        print("\n=== PAGINATION KEYS VALUE ===")
        if "next_cursor" in data:
            print(f"next_cursor: {data['next_cursor']}")
        else:
            print("next_cursor: NOT FOUND")
            
        if "next_page_token" in data:
            print(f"next_page_token: {data['next_page_token']}")
        else:
            print("next_page_token: NOT FOUND")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_tiktok_response())
