import sys
import os
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.models.order import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient
from app.integrations.shopee import ShopeeClient
from app.services.order_service import OrderService

# Setup DB
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import asyncio

async def check_status_async(target_date_str=None):
    db = SessionLocal()
    try:
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        else:
            target_date = datetime.now().date()

        print(f"🔍 Checking Order Statuses for Date: {target_date}")
        print("-" * 100)
        print(f"{'External ID':<20} | {'Channel':<10} | {'Time':<8} | {'Local Status':<20} | {'Remote Status':<20} | {'Match?'}")
        print("-" * 100)

        # Query Orders
        orders = db.query(OrderHeader).filter(
            func.date(OrderHeader.order_datetime) == target_date
        ).order_by(OrderHeader.order_datetime.desc()).all()

        if not orders:
            print(f"❌ No orders found for {target_date}")
            return

        # Get TikTok Config
        tiktok_config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'tiktok', PlatformConfig.is_active == True).first()
        if not tiktok_config:
            print("⚠️ No Active TikTok Configuration found in DB.")
            tiktok_client = None
        else:
            tiktok_client = TikTokClient(
                app_key=tiktok_config.app_key,
                app_secret=tiktok_config.app_secret,
                shop_id=tiktok_config.shop_id,
                access_token=tiktok_config.access_token,
                refresh_token=tiktok_config.refresh_token
            )

        match_count = 0
        mismatch_count = 0
        error_count = 0

        for order in orders:
            local_status = order.status_normalized
            remote_status = "N/A"
            match_symbol = "❓"
            time_str = order.order_datetime.strftime('%H:%M:%S') if order.order_datetime else "--:--"

            try:
                if order.channel_code == 'tiktok':
                    if not tiktok_client:
                        remote_status = "No Config"
                        match_symbol = "⚠️"
                        error_count += 1
                    else:
                        # Use existing client logic (Async)
                        tik_order = await tiktok_client.get_order_detail(order.external_order_id)
                        if tik_order:
                            remote_raw = tik_order.get('status', 'Unknown')
                            remote_status = tiktok_client.normalize_order_status(remote_raw)
                            display_remote = f"{remote_status} ({remote_raw})"
                            
                            if local_status == remote_status:
                                match_symbol = "✅"
                                match_count += 1
                            else:
                                match_symbol = "❌"
                                mismatch_count += 1
                        else:
                            display_remote = "Not Found (API)"
                            match_symbol = "❌"
                            error_count += 1
                
                elif order.channel_code == 'shopee':
                    display_remote = "Shopee-Skip" 
                    match_symbol = "➖"
                
                else:
                    display_remote = "Manual/Other"
                    match_symbol = "➖"

            except Exception as e:
                display_remote = f"Err: {str(e)[:10]}"
                error_count += 1
                match_symbol = "⚠️"

            # Print Row
            print(f"{order.external_order_id:<20} | {order.channel_code:<10} | {time_str:<8} | {local_status:<20} | {display_remote:<30} | {match_symbol}")

        print("-" * 100)
        print(f"📊 Summary: Total {len(orders)} | ✅ Matches: {match_count} | ❌ Mismatches: {mismatch_count} | ⚠️ Errors: {error_count}")
        if mismatch_count > 0:
            print("\n💡 Tip: Run 'python scripts/sync/update_order_status.py' to fix mismatches.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check Daily Order Status')
    parser.add_argument('--date', type=str, help='YYYY-MM-DD', default=None)
    args = parser.parse_args()
    
    asyncio.run(check_status_async(args.date))
