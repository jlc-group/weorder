import logging
import asyncio
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import OrderHeader
from app.integrations.tiktok import TikTokClient

logging.basicConfig(level=logging.INFO)

async def debug_payload(internal_id_str):
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        order = db.query(OrderHeader).get(internal_id_str)
        if not order:
            print("Order not found in DB")
            return

        print(f"Checking External Order ID: {order.external_order_id}")
        
        # Init Client
        # We need shop_id from somewhere or assume default
        # The client usually needs credentials.
        # We can grab credentials from settings or hardcode logic if needed,
        # but TikTokClient fetches from DB if we pass shop_id.
        
        # Let's verify how to init client.
        # TikTokClient(db, shop_id)
        # We get shop_id from channel or assume main.
        
        # Usually we sync using OrderService which handles client init.
        # Here we just want to fetch pure payload.
        
        # We need a valid Shop ID.
        # Let's try to infer from order (if we store shop_id? No, we store Company/Warehouse)
        # We store channel_code.
        
        # Load Config from PlatformConfig (Integration Service)
        from app.models.integration import PlatformConfig
        
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'tiktok',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("TikTok PlatformConfig not found")
            return
            
        print(f"Using Shop: {config.shop_name} ({config.shop_id})")
        
        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        print(f"Fetching Bundle Payload for Order {order.external_order_id}...")
        try:
            data = await client.get_order_detail(order.external_order_id)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error fetching: {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_payload("d03f29a3-de4b-4b17-a7f0-37f7e6034c51"))
