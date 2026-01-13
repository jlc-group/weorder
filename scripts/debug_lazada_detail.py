import asyncio
from sqlalchemy import create_engine
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.integrations.lazada import LazadaClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_lazada():
    db = SessionLocal()
    order_id = "1072648316130669"  # From previous debug list
    
    # Get Config
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    if not config:
        print("No active Lazada config")
        return

    client = LazadaClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    print(f"Fetching details for {order_id}...")
    try:
        # Get Detail
        detail = await client.get_order_detail(order_id)
        print("--- Order Detail ---")
        print(detail)
        
        # Get Items Raw
        raw_items = await client._make_request("/order/items/get", params={"order_id": order_id})
        print("--- Raw Items Response ---")
        print(raw_items)
        # items = await client.get_order_items(order_id)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_lazada())
