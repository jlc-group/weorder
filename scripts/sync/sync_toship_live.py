import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.core import settings, engine
from sqlalchemy.orm import sessionmaker
from app.services.sync_service import OrderSyncService
from app.models.integration import PlatformConfig
from app.integrations.shopee import ShopeeClient

async def sync_toship_live():
    print("Starting Live Sync for 'To Ship' Orders (Shopee)...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get Shopee Config
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == 'shopee',
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("Error: No active Shopee configuration found.")
            return

        service = OrderSyncService(db)
        client = ShopeeClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )
        
        # 1. Sync READY_TO_SHIP
        print("Fetching status: READY_TO_SHIP...")
        await sync_status(service, client, config, 'READY_TO_SHIP')
        
        # 2. Sync PROCESSED (Packing)
        print("Fetching status: PROCESSED...")
        await sync_status(service, client, config, 'PROCESSED')
        
    finally:
        db.close()
        print("\nSync Completed.")

async def sync_status(service, client, config, status):
    # Shopee limit: 15 days per request
    # We scan last 60 days in 15-day chunks
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=15), end_date)
        print(f"  > Scanning {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}...")
        
        cursor = ""
        while True:
            try:
                res = await client.get_orders(
                    status=status,
                    cursor=cursor,
                    page_size=50,
                    time_from=current_start,
                    time_to=current_end
                )
                
                orders = res.get("orders", [])
                if orders:
                    print(f"    - Found {len(orders)} orders")
                
                for raw_order in orders:
                    detail = await client.get_order_detail(raw_order.get("order_sn"))
                    if detail:
                        normalized = client.normalize_order(detail)
                        # Process order with existing DB session
                        # We need to manually call _process_order from service
                        # Get company first
                        from app.models.master import Company
                        company = service.db.query(Company).first()
                        
                        created, updated = service._process_order(normalized, company.id)
                        if created or updated:
                            print(f"      - Synced: {normalized.platform_order_id} ({normalized.status_normalized})")
                
                if not res.get("has_more"):
                    break
                    
                cursor = res.get("next_cursor")
                if not cursor:
                    break
                    
            except Exception as e:
                print(f"    Error in chunk: {e}")
                break
        
        current_start = current_end

if __name__ == "__main__":
    asyncio.run(sync_toship_live())
