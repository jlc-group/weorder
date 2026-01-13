import sys
import os
from app.core import get_db
from app.models.integration import PlatformConfig

# Add project root to path
sys.path.append(os.getcwd())

def update_lazada_config():
    db = next(get_db())
    print("--- Updating Lazada Config to Correct App Key ---")

    # Find existing Lazada config
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada').first()
    
    if config:
        print(f"Found existing Lazada config (ID: {config.id})")
        print(f"  Old App Key: {config.app_key}")
        
        # Update with new credentials from user
        # config.app_key = "129831"
        # config.app_secret = "atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y"
        # config.shop_name = "Julaherb (Lazada) - Seller In-house"
        
        # New Tokens
        config.access_token = "50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K"
        config.refresh_token = "50001300c15tHKDoxtuDe2Fzcjx1d63d585atRheFcP8kyVFjFvJXgxWF28Elk0N"
        
        # Expires in 2592000 seconds (30 days) from now
        from datetime import datetime, timedelta
        config.token_expires_at = datetime.utcnow() + timedelta(seconds=2592000)
        
        # Ensure shop_id matches
        config.shop_id = "100180059813" # from user_id/seller_id in JSON

        print(f"  ✅ Updated Tokens")
        print(f"  ✅ Expiration set to: {config.token_expires_at}")
    else:
        # Create if not exists
        print("Creating NEW Lazada config")
        from datetime import datetime, timedelta
        config = PlatformConfig(
            platform="lazada",
            shop_id="100180059813",
            shop_name="Julaherb (Lazada) - Seller In-house",
            app_key="129831",
            app_secret="atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y",
            access_token="50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K",
            refresh_token="50001300c15tHKDoxtuDe2Fzcjx1d63d585atRheFcP8kyVFjFvJXgxWF28Elk0N",
            token_expires_at=datetime.utcnow() + timedelta(seconds=2592000),
            is_active=True,
            sync_enabled=True,
            sync_interval_minutes=60
        )
        db.add(config)
        print("  ✅ Created new config with tokens")

    db.commit()
    print("Database updated successfully.")

if __name__ == "__main__":
    update_lazada_config()
