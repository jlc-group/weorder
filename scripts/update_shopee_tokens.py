import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import PlatformConfig

def update_shopee_tokens():
    db = SessionLocal()
    try:
        # User provided data
        partner_id = "2007239"
        shop_id = "240738298"
        access_token = "eyJhbGciOiJIUzI1NiJ9.CMfBehABGPq_5XIgASjXnKjKBjDo9auWAzgBQAE.91ezuaHPY3Llj3JVaLr_heXiZfRJGGisW_DZHl6GVaM"
        refresh_token = "eyJhbGciOiJIUzI1NiJ9.CMfBehABGPq_5XIgAijXnKjKBjDFuqqVCzgBQAE.FUvAgnVdGgM8-yLkhiMcsJ6PVRPtPkOHt6PcE7Ye6wc"
        expire_in = 14400  # 4 hours
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(seconds=expire_in)
        
        print(f"Looking for Shopee config for shop_id: {shop_id}...")
        
        # Find config
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == "shopee",
            PlatformConfig.shop_id == shop_id
        ).first()
        
        if not config:
            print(f"Config not found! Creating new one...")
            # If not found, look for ANY shopee config to update, or create new
            config = db.query(PlatformConfig).filter(PlatformConfig.platform == "shopee").first()
            
            if config:
                print(f"Found existing generic Shopee config (ID: {config.id}). Updating...")
        
        if config:
            config.access_token = access_token
            config.refresh_token = refresh_token
            config.token_expires_at = expires_at
            config.shop_id = shop_id
            config.partner_id = partner_id
            config.is_active = True
            
            db.commit()
            print(f"Successfully updated Shopee tokens!")
            print(f"Access Token: {config.access_token[:10]}...")
            print(f"Expires At: {config.token_expires_at}")
        else:
            print("No Shopee configuration found to update.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_shopee_tokens()
