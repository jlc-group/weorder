#!/usr/bin/env python3
"""
Re-process all pending webhooks that were not processed
Run: python reprocess_webhooks.py
"""
import asyncio
from datetime import datetime
from app.core.database import SessionLocal
from app.services.sync_service import OrderSyncService
from app.services import integration_service
from sqlalchemy import text

async def reprocess_pending_webhooks():
    db = SessionLocal()
    
    try:
        # Get all unprocessed webhooks
        result = db.execute(text("""
            SELECT id::text, platform, event_type, payload
            FROM webhook_log 
            WHERE processed = false
            AND platform = 'tiktok'
            ORDER BY received_at ASC
        """))
        
        pending = list(result)
        total = len(pending)
        print(f"🔄 Found {total} pending webhooks to process")
        
        service = OrderSyncService(db)
        processed = 0
        skipped = 0
        errors = 0
        
        for row in pending:
            webhook_id, platform, event_type, payload = row
            
            try:
                data = payload.get('data', {}) if payload else {}
                order_id = data.get('order_id', '')
                
                if not order_id:
                    # Mark as processed without order_id
                    db.execute(text(f"UPDATE webhook_log SET processed=true, process_result='NO_ORDER_ID' WHERE id::text='{webhook_id}'"))
                    skipped += 1
                    continue
                
                # Process the order
                created, updated = await service.process_webhook_order(
                    platform=platform,
                    order_id=str(order_id),
                    event_type=str(event_type),
                )
                
                result_str = "CREATED" if created else ("UPDATED" if updated else "SKIPPED")
                
                # Mark webhook as processed
                db.execute(text(f"UPDATE webhook_log SET processed=true, processed_at=NOW(), process_result='{result_str}' WHERE id::text='{webhook_id}'"))
                db.commit()
                
                processed += 1
                
                if processed % 50 == 0:
                    print(f"   Processed {processed}/{total} ({processed*100//total}%)")
                    
            except Exception as e:
                db.execute(text(f"UPDATE webhook_log SET processed=true, process_error='{str(e)[:200]}' WHERE id::text='{webhook_id}'"))
                db.commit()
                errors += 1
        
        print(f"\n✅ Done!")
        print(f"   Processed: {processed}")
        print(f"   Skipped: {skipped}")
        print(f"   Errors: {errors}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(reprocess_pending_webhooks())
