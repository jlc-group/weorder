
import asyncio
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
from app.services import integration_service
from app.models.integration import PlatformConfig

async def test_tiktok_reverse():
    db = SessionLocal()
    try:
        # Find TikTok Config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'tiktok', PlatformConfig.is_active == True).first()
        if not config:
            print("No active TikTok config found")
            return

        client = integration_service.get_client_for_config(config)
        
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=30)
        
        print(f"Fetching reverse orders for {config.shop_name} from {time_from} to {time_to}...")
        
        try:
            resp = await client.get_reverse_orders(time_from, time_to)
            print("Response Keys:", resp.keys())
            
            # Check for common keys: 'returns', 'reverse_orders', 'reverse_list'
            for key in ['returns', 'reverse_orders', 'reverse_list']:
                items = resp.get(key)
                if items is not None:
                    print(f"Found key '{key}' with {len(items)} items")
                    if len(items) > 0:
                        print("Sample Item:", items[0])
            
            if not any(resp.get(k) for k in ['returns', 'reverse_orders', 'reverse_list']):
                print("No obvious returns list found in response:", resp)
                
        except Exception as e:
            print(f"API Error: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_tiktok_reverse())
