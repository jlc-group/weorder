"""
Webhook Processor - Background service to process pending webhooks in real-time
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services import integration_service, sync_service

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Background processor for pending webhooks"""
    
    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self.is_running = False
        self.last_poll: datetime = None
        self.processed_count: int = 0
        self.last_minute_count: int = 0
        self._task = None
        
    async def start(self):
        """Start the background processor"""
        if self.is_running:
            logger.warning("Webhook processor already running")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"[OK] Webhook processor started (polling every {self.poll_interval}s)")
        
    async def stop(self):
        """Stop the background processor"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Webhook processor stopped")
        
    async def _run_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                await self._process_pending()
            except Exception as e:
                logger.error(f"Webhook processor error: {e}")
            
            # Wait before next poll
            await asyncio.sleep(self.poll_interval)
    
    async def _process_pending(self):
        """Process all pending webhooks"""
        db: Session = SessionLocal()
        try:
            # Get unprocessed webhooks
            webhooks = integration_service.get_unprocessed_webhooks(db, limit=50)
            
            if not webhooks:
                self.last_poll = datetime.utcnow()
                return
            
            logger.info(f"[PROCESSING] {len(webhooks)} pending webhooks")
            
            processed = 0
            for webhook in webhooks:
                try:
                    # Extract order_id from payload
                    order_id = self._extract_order_id(webhook.platform, webhook.payload)
                    
                    if order_id:
                        # Process the webhook
                        service = sync_service.OrderSyncService(db)
                        created, updated = await service.process_webhook_order(
                            platform=webhook.platform,
                            order_id=order_id,
                            event_type=webhook.event_type,
                        )
                        
                        result = "CREATED" if created else ("UPDATED" if updated else "SKIPPED")
                        integration_service.mark_webhook_processed(db, str(webhook.id), result)
                        processed += 1
                        
                        logger.debug(f"  [OK] {webhook.platform}/{order_id} -> {result}")
                    else:
                        # No order_id found, mark as skipped
                        integration_service.mark_webhook_processed(db, str(webhook.id), "SKIPPED", "No order_id in payload")
                        
                except Exception as e:
                    logger.error(f"  [FAIL] Failed to process webhook {webhook.id}: {e}")
                    integration_service.mark_webhook_processed(db, str(webhook.id), "FAILED", str(e))
            
            self.processed_count += processed
            self.last_minute_count = processed
            self.last_poll = datetime.utcnow()
            
            logger.info(f"[DONE] Processed {processed}/{len(webhooks)} webhooks")
            
        except Exception as e:
            logger.error(f"Error in webhook processing: {e}")
        finally:
            db.close()
    
    def _extract_order_id(self, platform: str, payload: dict) -> str:
        """Extract order ID from webhook payload"""
        if not payload:
            return None
            
        if platform == "shopee":
            return payload.get("data", {}).get("ordersn")
        elif platform == "lazada":
            return str(payload.get("data", {}).get("trade_order_id", ""))
        elif platform == "tiktok":
            return payload.get("data", {}).get("order_id")
        
        return None
    
    def get_status(self) -> Dict:
        """Get processor status"""
        return {
            "is_running": self.is_running,
            "poll_interval": self.poll_interval,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "total_processed": self.processed_count,
            "last_batch_count": self.last_minute_count,
        }


# Singleton instance
_processor: WebhookProcessor = None


def get_processor() -> WebhookProcessor:
    """Get or create the webhook processor instance"""
    global _processor
    if _processor is None:
        _processor = WebhookProcessor(poll_interval=30)
    return _processor


async def start_webhook_processor():
    """Start the webhook processor"""
    processor = get_processor()
    await processor.start()


async def stop_webhook_processor():
    """Stop the webhook processor"""
    processor = get_processor()
    await processor.stop()
