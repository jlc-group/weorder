import sys
import os
from datetime import datetime, timedelta
from app.core import get_db
from app.models.integration import PlatformConfig

# Add project root to path
sys.path.append(os.getcwd())

def add_tokens():
    db = next(get_db())
    print("--- Updating Platform Tokens ---")

    # 1. SHOPEE Configuration
    # Data from user JSON + mapped secret from previous context
    shopee_data = {
        "platform": "shopee",
        "shop_id": "240738298",
        "shop_name": "Julaherb (Shopee Main)", # Placeholder name
        "app_key": "2007100", # partner_id
        "app_secret": "51487a7578596b62684f5362734f56664c56426253657658634c6b5263454572", # Mapped from Step 698 comments for 2007100
        "access_token": "eyJhbGciOiJIUzI1NiJ9.CLzAehABGPq_5XIgASjQuIfABjCWrvnlBTgBQAE.iTdRc9dNsdkNkPweomWcKPYpdyVQP3OJFSyc2MMmJ2I",
        "refresh_token": "eyJhbGciOiJIUzI1NiJ9.CLzAehABGPq_5XIgAijQuIfABjDs9OyVCzgBQAE.ZdnvMebG-V4VlyHM1WnKsjWECR-NlrykTX1tftSTXu0",
        "token_expires_at": datetime.now() + timedelta(seconds=14400), # expire_in 14400
        "is_active": True,
        "sync_enabled": True,
        "sync_interval_minutes": 60
    }

    # 2. LAZADA Configuration
    # Data from user JS snippet
    lazada_data = {
        "platform": "lazada",
        "shop_id": "lazada_main", # No specific shop_id provided in JS, using generic unique ID
        "shop_name": "Julaherb (Lazada)", 
        "app_key": "105827",
        "app_secret": "r8ZMKhPxu1JZUCwTUBVMJiJnZKjhWeQF",
        "access_token": "cd074c370f324587a5cedb1daf71bddf", # From code/access_token var
        "refresh_token": None, # Not provided in snippet
        "is_active": True,
        "sync_enabled": True,
        "sync_interval_minutes": 60
    }

    configs = [shopee_data, lazada_data]

    for data in configs:
        platform = data['platform']
        print(f"Processing {platform.upper()}...")
        
        # Check existing by platform AND app_key (to avoid mixing different apps)
        existing = db.query(PlatformConfig).filter(
            PlatformConfig.platform == platform,
            PlatformConfig.app_key == data['app_key']
        ).first()

        if existing:
            print(f"  Updating existing config for {platform} (ID: {existing.id})")
            existing.access_token = data['access_token']
            if data['refresh_token']:
                existing.refresh_token = data['refresh_token']
            existing.app_secret = data['app_secret']
            existing.shop_id = data['shop_id']
            existing.token_expires_at = data.get('token_expires_at')
            existing.is_active = True
        else:
            print(f"  Creating NEW config for {platform}")
            new_config = PlatformConfig(**data)
            db.add(new_config)
    
    db.commit()
    print("✅ Database updated successfully.")

if __name__ == "__main__":
    add_tokens()
