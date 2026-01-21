"""
Reprocess Pending Webhooks
- ดึง webhooks ที่ยังไม่ได้ process
- ดึงข้อมูล order จาก API ตาม order_id ใน webhook
- อัพเดท orders ใน DB
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.integration import WebhookLog, PlatformConfig
from app.services.sync_service import OrderSyncService
from datetime import datetime

# DB Setup
db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def reprocess_webhooks(limit: int = 500):
    db = SessionLocal()
    try:
        # Get pending webhooks (not processed)
        pending = db.query(WebhookLog).filter(
            WebhookLog.processed == False
        ).order_by(WebhookLog.received_at.desc()).limit(limit).all()
        
        print(f"📋 Found {len(pending)} pending webhooks to process")
        
        if not pending:
            print("✅ No pending webhooks")
            return
        
        # Group by platform
        platforms = {}
        for webhook in pending:
            if webhook.platform not in platforms:
                platforms[webhook.platform] = []
            
            # Extract order_id from payload - different for each platform
            payload = webhook.payload or {}
            data = payload.get("data", {})
            
            order_id = None
            if webhook.platform == "tiktok":
                order_id = data.get("order_id") or payload.get("order_id")
            elif webhook.platform == "lazada":
                order_id = str(data.get("trade_order_id", "")) or payload.get("order_id")
            elif webhook.platform == "shopee":
                order_id = data.get("ordersn") or payload.get("ordersn") or payload.get("order_id")
            else:
                order_id = data.get("order_id") or payload.get("order_id")
            
            if order_id:
                platforms[webhook.platform].append({
                    "webhook": webhook,
                    "order_id": order_id,
                    "event_type": webhook.event_type
                })
        
        print(f"\n📊 Webhooks by platform:")
        for platform, items in platforms.items():
            print(f"   {platform}: {len(items)}")
        
        # Process each platform
        sync_service = OrderSyncService(db)
        processed = 0
        errors = 0
        
        for platform, items in platforms.items():
            print(f"\n🔄 Processing {platform} webhooks...")
            
            for item in items:
                try:
                    order_id = item["order_id"]
                    event_type = item["event_type"]
                    webhook = item["webhook"]
                    
                    # Process webhook order
                    created, updated = await sync_service.process_webhook_order(
                        platform=platform,
                        order_id=order_id,
                        event_type=str(event_type),
                    )
                    
                    result = "CREATED" if created else ("UPDATED" if updated else "SKIPPED")
                    webhook.mark_processed(result)
                    processed += 1
                    
                    if processed % 50 == 0:
                        print(f"   Processed: {processed}/{len(pending)}", end="\r")
                        db.commit()
                    
                except Exception as e:
                    errors += 1
                    webhook = item["webhook"]
                    webhook.mark_processed("FAILED", str(e))
                    
                await asyncio.sleep(1.0)  # Slower rate to avoid TikTok API limit
        
        db.commit()
        
        print(f"\n\n✅ Completed!")
        print(f"   Processed: {processed}")
        print(f"   Errors: {errors}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    asyncio.run(reprocess_webhooks(limit))
