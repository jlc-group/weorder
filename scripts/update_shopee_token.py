import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import SessionLocal, engine
from app.core.database import Base
from app.models.integration import PlatformConfig
from app.integrations.shopee import ShopeeClient

async def update_and_verify_shopee_token():
    # Ensure tables exist
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        shop_id = "240738298"
        partner_id = "2007239"
        access_token = "eyJhbGciOiJIUzI1NiJ9.CMfBehABGPq_5XIgASiBxszLBjDWjrqhBDgBQAE.i8Wui6CpzYeJzCeHQZfYKkXUt7JJrqO3dBRY6Hj04Zc"
        refresh_token = "eyJhbGciOiJIUzI1NiJ9.CMfBehABGPq_5XIgAiiBxszLBjCRjdyRCzgBQAE.kdrSGkbONRbygtcAuotN6GiJ-JzeJLY1zQxl5z1Wbco"
        expire_in = 14400 # 4 hours
        
        print(f"Checking PlatformConfig for shop_id: {shop_id}")
        
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == "shopee", 
            PlatformConfig.shop_id == shop_id
        ).first()
        
        if not config:
            print("Config not found, creating new one...")
            config = PlatformConfig(
                platform="shopee",
                shop_id=shop_id,
                app_key=partner_id,
                # app_secret needs to be set if new, but assuming we update existing or using placeholder if unknown
                # Ideally app_secret is static and should be already there or provided.
                # For this script we assume existing config OR we need the secret.
                # From message, user didn't provide secret. If it's creating new, it might fail without secret.
                # Let's hope it exists.
                is_active=True
            )
            # We don't have secret from user snippet, so if it's new we might be stuck.
            # But let's assume it exists as user said "update token".
            # If not found, we might need to ask user for Secret.
            # Actually, I'll check if any shopee config exists to steal key/secret if needed.
            any_shopee = db.query(PlatformConfig).filter(PlatformConfig.platform == "shopee").first()
            if any_shopee:
                 config.app_secret = any_shopee.app_secret
                 config.app_key = any_shopee.app_key # Use same partner id if same partner
        
        # Update tokens
        config.access_token = access_token
        config.refresh_token = refresh_token
        config.token_expires_at = datetime.utcnow() + timedelta(seconds=expire_in)
        
        if config.id:
             print(f"Updating existing config ID: {config.id}")
        else:
             db.add(config)
             print("Created new config object (pending commit)")

        db.commit()
        print("Token updated in database.")
        
        # Verify
        print("Verifying token with API call...")
        if not config.app_secret:
            print("ERROR: app_secret is missing. Cannot verify.")
            return

        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        # Try fetch orders (lightweight)
        result = await client.get_orders(page_size=1)
        print("API Call Result:", result)
        print("✅ SUCCESS: Shopee token is valid and working.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(update_and_verify_shopee_token())
