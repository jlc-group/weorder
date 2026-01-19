"""
Sync Cleanup Script
- ดึง orders จาก TikTok API ที่ status = AWAITING_SHIPMENT
- เปรียบเทียบกับ DB
- อัพเดท orders ที่ status เปลี่ยนไปแล้ว
"""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader
from app.integrations.tiktok import TikTokClient
from datetime import datetime, timedelta

# DB Setup
db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def run_cleanup():
    db = SessionLocal()
    try:
        # Get TikTok Config
        config = db.query(PlatformConfig).filter(
            PlatformConfig.platform == "tiktok", 
            PlatformConfig.is_active == True
        ).first()
        
        if not config:
            print("❌ No active TikTok configuration found.")
            return

        print(f"✅ TikTok Shop ID: {config.shop_id}")
        
        # Initialize Client
        client = TikTokClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )

        # 1. Get all PAID orders from DB (TikTok only)
        db_paid_orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_normalized == 'PAID'
        ).all()
        
        print(f"📊 DB: {len(db_paid_orders)} TikTok orders with PAID status")
        
        # Create lookup by external_order_id
        db_order_map = {o.external_order_id: o for o in db_paid_orders}
        
        # 2. Fetch all AWAITING_SHIPMENT from API
        print(f"\n🔍 Fetching AWAITING_SHIPMENT orders from TikTok API...")
        api_order_ids = set()
        cursor = None
        page = 1
        
        while True:
            result = await client.get_orders(
                time_from=datetime.utcnow() - timedelta(days=90),
                status="AWAITING_SHIPMENT",
                cursor=cursor,
                page_size=50
            )
            
            orders = result.get("orders", [])
            for order in orders:
                if order.get("status") == "AWAITING_SHIPMENT":
                    api_order_ids.add(order.get("id"))
            
            print(f"   Page {page}: {len(orders)} orders, total valid: {len(api_order_ids)}", end="\r")
            
            cursor = result.get("next_cursor") or result.get("cursor")
            if not cursor or not result.get("has_more", result.get("more", False)):
                break
                
            page += 1
            await asyncio.sleep(0.3)
        
        print(f"\n✅ API: {len(api_order_ids)} AWAITING_SHIPMENT orders")
        
        # 3. Find orders in DB but NOT in API (status changed)
        stale_orders = []
        for ext_id, order in db_order_map.items():
            if ext_id not in api_order_ids:
                stale_orders.append(order)
        
        print(f"\n⚠️  Stale orders (in DB as PAID but not AWAITING_SHIPMENT in API): {len(stale_orders)}")
        
        if stale_orders:
            print("\n📋 Sample stale orders (first 10):")
            for i, o in enumerate(stale_orders[:10]):
                print(f"   {i+1}. {o.external_order_id} - Created: {o.order_datetime}")
            
            # 4. Fetch actual status from API for stale orders
            print(f"\n🔄 Fetching actual status for {min(len(stale_orders), 50)} stale orders...")
            
            batch_size = 50
            updated_count = 0
            status_changes = {}
            
            for i in range(0, min(len(stale_orders), 200), batch_size):
                batch = stale_orders[i:i+batch_size]
                order_ids = [o.external_order_id for o in batch]
                
                try:
                    details = await client.get_order_details_batch(order_ids)
                    
                    for detail in details:
                        order_id = detail.get("id")
                        new_status = detail.get("status")
                        
                        if order_id and new_status:
                            # Find in our batch
                            for o in batch:
                                if o.external_order_id == order_id:
                                    old_status = o.status_normalized
                                    # Map to our normalized status
                                    status_map = {
                                        "AWAITING_SHIPMENT": "PAID",
                                        "AWAITING_COLLECTION": "READY_TO_SHIP",
                                        "IN_TRANSIT": "SHIPPED",
                                        "DELIVERED": "DELIVERED",
                                        "COMPLETED": "COMPLETED",
                                        "CANCELLED": "CANCELLED",
                                    }
                                    normalized = status_map.get(new_status, new_status)
                                    
                                    if normalized != old_status:
                                        o.status_normalized = normalized
                                        o.status_raw = new_status
                                        updated_count += 1
                                        
                                        key = f"{old_status} -> {normalized}"
                                        status_changes[key] = status_changes.get(key, 0) + 1
                                    break
                    
                except Exception as e:
                    print(f"   ⚠️ Error fetching batch: {e}")
                
                await asyncio.sleep(0.5)
            
            if updated_count > 0:
                db.commit()
                print(f"\n✅ Updated {updated_count} orders:")
                for change, count in sorted(status_changes.items(), key=lambda x: -x[1]):
                    print(f"   {change}: {count}")
            else:
                print("\n✅ No status changes needed")
        
        # Final count
        final_paid = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.status_normalized == 'PAID'
        ).count()
        
        print(f"\n📊 Final TikTok PAID count in DB: {final_paid}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_cleanup())
