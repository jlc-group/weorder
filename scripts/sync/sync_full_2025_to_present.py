"""
Sync Orders from Jan 2025 to Present (All Platforms)
"""
import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.sync_service import OrderSyncService
from app.core import settings
from app.core.database import SessionLocal, engine

# Configure Logging (Silent Mode)
logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Force disable SQL echo
engine.echo = False

async def sync_all_platforms():
    print("=" * 60)
    print("FULL SYNC: Jan 2025 to Present (All Platforms)")
    print("=" * 60)
    
    db = SessionLocal()
    service = OrderSyncService(db)
    
    # Time range: Jan 1, 2025 to Now
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print("-" * 60)
    
    try:
        from app.models.integration import PlatformConfig
        
        # Get all active configs
        configs = db.query(PlatformConfig).filter(PlatformConfig.is_active == True).all()
        
        results = {}
        for config in configs:
            if config.platform in ['tiktok', 'lazada', 'shopee']:
                print(f"\n🔄 Syncing {config.platform.upper()} ({config.shop_name})...")
                try:
                    await service.sync_platform_orders(
                        config=config,
                        time_from=start_date,
                        time_to=end_date
                    )
                    results[config.platform] = "✅ Success"
                    print(f"   ✅ {config.platform} Sync Complete.")
                except Exception as e:
                    results[config.platform] = f"❌ Error: {e}"
                    print(f"   ❌ Error syncing {config.platform}: {e}")
        
        print("\n" + "=" * 60)
        print("SYNC SUMMARY:")
        for platform, status in results.items():
            print(f"  {platform}: {status}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error during overall sync: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_all_platforms())
