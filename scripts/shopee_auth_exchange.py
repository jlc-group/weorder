import asyncio
import sys
import os
sys.path.append(os.getcwd())
import logging
from datetime import datetime

from app.core import get_db
from app.services import integration_service
from app.integrations.shopee import ShopeeClient

# User provided
AUTH_CODE = "56486d59616c4f414f4a557478467779"
SHOP_ID = 240738298

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def exchange_auth():
    db = next(get_db())
    try:
        # Get Config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        config = configs[0]
        logger.info(f"Using config for {config.platform} (ID: {config.shop_id})")
        
        # Instantiate Client with NEW keys (already in DB) but we need to pass shop_id
        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=str(SHOP_ID)
        )
        
        logger.info(f"Exchanging Auth Code: {AUTH_CODE}...")
        try:
            tokens = await client.exchange_code_for_token(AUTH_CODE)
            logger.info("✅ Exchange Successful!")
            print(f"Tokens: {tokens}")
            
            # Update DB
            config.access_token = tokens['access_token']
            config.refresh_token = tokens['refresh_token']
            config.token_expires_at = datetime.utcnow().timestamp() + tokens['expires_in'] # timestamp
            # Convert timestamp to datetime if model expects datetime
            # Model expects datetime
            from datetime import timedelta
            config.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
            
            db.commit()
            logger.info("✅ Database updated with new tokens.")
            
        except Exception as e:
            logger.error(f"❌ Exchange Failed: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(exchange_auth())
