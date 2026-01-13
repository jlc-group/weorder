from sqlalchemy import create_engine, text
import logging
import asyncio
from app.core import SessionLocal
from app.models import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_single():
    db = SessionLocal()
    target_id = "581693998548878727"
    
    # Get config
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'tiktok', PlatformConfig.is_active == True).first()
    client = TikTokClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    print(f"Fetching detail for {target_id}...")
    details = await client.get_order_details_batch([target_id])
    
    if details:
        d = details[0]
        print("API Response Data:")
        print(f"update_time: {d.get('update_time')}")
        print(f"collection_time: {d.get('collection_time')}")
        print(f"rts_time: {d.get('rts_time')}")
        
        final_time = d.get('collection_time') or d.get('rts_time') or d.get('update_time')
        print(f"Calculated Final Time (Unix): {final_time}")
        
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(final_time, tz=timezone.utc)
        print(f"Calculated Final Time (ISO): {dt}")
    else:
        print("No details found from API")

if __name__ == "__main__":
    asyncio.run(debug_single())
