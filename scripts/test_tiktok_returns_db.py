
import asyncio
import os
import sys

# Setup environment
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient
from datetime import datetime, timedelta

# DB Setup
db_url = getattr(settings, "DATABASE_URL", None)
if not db_url:
    db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
# Fix for Windows if needed (asyncio vs uvloop? usually psycopg2 is sync)
# settings.DATABASE_URL usually is asyncpg? No, usually str.

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def verify_tiktok_returns():
    db = SessionLocal()
    try:
        # Get TikTok Config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == "tiktok", PlatformConfig.is_active == True).first()
        if not config:
            print("❌ No active TikTok configuration found.")
            return

        print(f"Found TikTok Config: Shop ID {config.shop_id}")
        
        # Initialize Client
        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )

        # Test params
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Fetching REVERSE orders (Returns/Cancellations)...")
        print(f"   - Time Range: Last 7 days (From {start_date.strftime('%Y-%m-%d %H:%M:%S')})")
        
        # This calls POST endpoints which rely on the signature fix
        result = await client.get_reverse_orders(
            update_time_from=start_date,
            update_time_to=end_date,
            page_size=10
        )
        
        returns = result.get("returns", [])
        print(f"Success! Found {len(returns)} reverse orders.")
        for r in returns:
            return_id = r.get('return_order_id') or r.get('cancel_order_id')
            status = r.get('return_status')
            print(f" - {return_id}: {status}")

    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Fix for Windows asyncio EventLoopPolicy if needed
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(verify_tiktok_returns())
