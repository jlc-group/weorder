import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID

from app.core.config import settings
from app.models import OrderHeader
from app.services import integration_service
from app.integrations import TikTokClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_label(order_id_str):
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"Checking Order ID: {order_id_str}")
        try:
            uuid_obj = UUID(order_id_str)
            order = db.query(OrderHeader).filter(OrderHeader.id == uuid_obj).first()
        except ValueError:
            order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id_str).first()
            
        if not order:
            print("❌ Order not found in DB")
            return

        print(f"✅ Found Order: {order.external_order_id}")
        print(f"Channel: {order.channel_code}")
        print(f"Status: {order.status_normalized} (Raw: {order.status_raw})")
        print(f"Shop ID: {order.company_id}") # This might not be shop_id, check integration linking
        
        platform = order.channel_code.lower()
        if platform != "tiktok":
            print(f"❌ Platform is not tiktok: {platform}")
            return

        configs = integration_service.get_platform_configs(db, platform=platform, is_active=True)
        if not configs:
            print("❌ No active platform config found for tiktok")
            return
            
        config = configs[0]
        print(f"Using Config: {config.shop_name} (ID: {config.shop_id})")
        
        client = integration_service.get_client_for_config(config)
        
        print("Attempting to fetch label URL...")
        try:
            url = await client.get_shipping_label(order.external_order_id)
            if url:
                print(f"✅ Success! Label URL: {url}")
            else:
                print("❌ Failed. No URL returned (None).")
        except Exception as e:
            print(f"❌ Exception during API call: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_label("5e4490c2-96c8-410a-bfca-79238494c3bb"))
