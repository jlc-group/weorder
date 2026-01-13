import asyncio
import sys, os
from datetime import datetime
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import PlatformConfig
from app.integrations.shopee import ShopeeClient

async def refresh_shopee():
    db = SessionLocal()
    try:
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "shopee", PlatformConfig.is_active == True).first()
        if not config:
            print("Shopee config not found")
            return

        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )

        print(f"Refreshing token for Shop ID: {config.shop_id}")
        new_tokens = await client.refresh_access_token()
        
        config.access_token = new_tokens["access_token"]
        config.refresh_token = new_tokens["refresh_token"]
        config.updated_at = datetime.utcnow()
        
        db.commit()
        print("Token refreshed and saved successfully!")
        
    except Exception as e:
        print(f"Error refreshing token: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(refresh_shopee())
