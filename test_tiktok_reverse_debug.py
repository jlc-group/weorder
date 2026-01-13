
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_tiktok_reverse")

from app.core.database import SessionLocal
from app.services import integration_service
from app.models.integration import PlatformConfig

async def test_tiktok_reverse():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'tiktok', PlatformConfig.is_active == True).first()
        if not config:
            logger.error("No active TikTok config found")
            return

        client = integration_service.get_client_for_config(config)
        
        time_to = datetime.utcnow()
        time_from = time_to - timedelta(days=30)
        
        logger.info(f"Testing TikTok Reverse API for {config.shop_name}")
        
        # Try both GET and POST search
        tests = [
            {"path": f"/reverse/202309/reverse_orders", "method": "GET"},
            {"path": f"/reverse/202309/reverse_orders/search", "method": "POST", "body": {
                "update_time_from": int(time_from.timestamp()),
                "update_time_to": int(time_to.timestamp()),
                "page_size": 20
            }}
        ]
        
        for t in tests:
            logger.info(f"Testing {t['method']} {t['path']}...")
            try:
                # Use _make_request directly to bypass the hardcoded logic if needed
                resp = await client._make_request(
                    t["path"], 
                    method=t["method"], 
                    body=t.get("body")
                )
                logger.info(f"SUCCESS {t['path']}: Keys: {list(resp.keys())}")
                # Check for list of items
                for key in ['reverse_orders', 'reverse_list', 'reverse_order_list', 'returns']:
                    if key in resp:
                        items = resp.get(key, [])
                        logger.info(f"Found key '{key}' with {len(items)} items")
            except Exception as e:
                logger.error(f"FAILED {t['path']}: {e}")
                
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_tiktok_reverse())
