import sys
import os
import logging
from datetime import datetime, timedelta

# Setup path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import PlatformConfig

# ==========================================
# 🟢 ใส่ Token ใหม่ของคุณตรงนี้ (Replace with NEW tokens)
# ==========================================

NEW_TOKENS = {
    "shopee": {
        "access_token": "YOUR_SHOPEE_ACCESS_TOKEN_HERE", 
        "refresh_token": "YOUR_SHOPEE_REFRESH_TOKEN_HERE",
        "expire_in_seconds": 14400 # 4 hours
    },
    "lazada": {
        "access_token": "YOUR_LAZADA_ACCESS_TOKEN_HERE",
        "refresh_token": "YOUR_LAZADA_REFRESH_TOKEN_HERE", 
        "expire_in_seconds": 2592000 # 30 days
    }
}

# ==========================================

def update_tokens():
    db = SessionLocal()
    try:
        print("--- Updating Tokens in Database ---")
        
        for platform, data in NEW_TOKENS.items():
            if "YOUR_" in data["access_token"]:
                print(f"⚠️  Skipping {platform}: Token not filled in.")
                continue
                
            config = db.query(PlatformConfig).filter(PlatformConfig.platform == platform).first()
            if config:
                print(f"✅ Found {platform} (Shop: {config.shop_name})")
                
                config.access_token = data["access_token"]
                config.refresh_token = data["refresh_token"]
                config.token_expires_at = datetime.utcnow() + timedelta(seconds=data["expire_in_seconds"])
                
                print(f"   - Updated Access Token")
                print(f"   - Updated Refresh Token")
                print(f"   - New Expiry: {config.token_expires_at}")
            else:
                print(f"❌ {platform} config not found in DB.")

        db.commit()
        print("\n✅ Database saved successfully.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_tokens()
