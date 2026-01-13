import sys
import os
from datetime import datetime
from app.core import get_db
from app.models.integration import PlatformConfig

# Add project root to path
sys.path.append(os.getcwd())

def check_tokens():
    db = next(get_db())
    print(f"--- Checking Platform Tokens (at {datetime.now()}) ---")
    
    configs = db.query(PlatformConfig).filter(PlatformConfig.is_active == True).all()
    
    if not configs:
        print("❌ No active platforms found.")
        return

    platforms_found = []
    for config in configs:
        platforms_found.append(config.platform)
        print(f"\nPlatform: {config.platform.upper()}")
        print(f"  Shop Detail: {config.shop_name} (ID: {config.shop_id})")
        print(f"  Access Token: {'✅ Present' if config.access_token else '❌ Missing'}")
        print(f"  Refresh Token: {'✅ Present' if config.refresh_token else '❌ Missing'}")
        
        if config.token_expires_at:
            delta = config.token_expires_at - datetime.now()
            days = delta.days
            seconds = delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            
            if delta.total_seconds() > 0:
                print(f"  Expires in: {days}d {hours}h {minutes}m ({config.token_expires_at}) -> ✅ Valid")
            else:
                print(f"  Expires in: {days}d {hours}h {minutes}m ({config.token_expires_at}) -> ⚠️ EXPIRED")
        else:
            print("  Expires in: Unknown (No expiration date set)")
            
    # Check for missing platforms
    expected_platforms = ['shopee', 'lazada', 'tiktok']
    missing = [p for p in expected_platforms if p not in platforms_found]
    
    print("\n--- Summary ---")
    if missing:
        print(f"⚠️ Missing active tokens for: {', '.join(missing).upper()}")
    else:
        print("✅ All major platforms (Shopee, Lazada, TikTok) have active configs.")

if __name__ == "__main__":
    check_tokens()
