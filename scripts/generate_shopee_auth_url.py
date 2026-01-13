import asyncio
import sys
import os
sys.path.append(os.getcwd())
try:
    from app.core import get_db
    from app.services import integration_service
    from app.integrations.shopee import ShopeeClient
except ImportError:
    # Fallback if running outside app context
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from app.core import get_db
    from app.services import integration_service
    from app.integrations.shopee import ShopeeClient

async def get_url():
    db = next(get_db())
    try:
        # Get Config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        config = configs[0]
        
        client = integration_service.get_client_for_config(config)
        
        # Redirect URI (Usually your callback URL or localhost)
        # Assuming user has set this in Shopee Console.
        # Since we don't know it, we can try a generic one or ask user.
        # But wait, signature depends on it.
        # Let's try "https://google.com" or "http://localhost" as placeholders
        redirect_uri = "https://admindashboard-weorder.vercel.app/callback" # Common one?
        # Or maybe the user knows?
        # I'll output the URL and say "Make sure Redirect URI matches what you set in Shopee Console"
        
        url = await client.get_auth_url(redirect_uri)
        print(f"Auth URL: {url}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(get_url())
