"""
Webhook API Endpoints - Receive notifications from marketplace platforms
"""
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import logging

from app.core.database import get_db
from app.services import integration_service, sync_service
from app.integrations import ShopeeClient, LazadaClient, TikTokClient

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def process_order_webhook(
    db: Session,
    platform: str,
    order_id: str,
    event_type: str,
    webhook_log_id: str,
):
    """Background task to process webhook order"""
    try:
        service = sync_service.OrderSyncService(db)
        created, updated = await service.process_webhook_order(
            platform=platform,
            order_id=order_id,
            event_type=event_type,
        )
        
        result = "CREATED" if created else ("UPDATED" if updated else "SKIPPED")
        await run_in_threadpool(integration_service.mark_webhook_processed, db, webhook_log_id, result)
        
        logger.info(f"Webhook processed: {platform}/{order_id} -> {result}")
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {platform}/{order_id} - {e}")
        await run_in_threadpool(integration_service.mark_webhook_processed, db, webhook_log_id, "FAILED", str(e))


# ========== Shopee Webhook ==========

@webhook_router.post("/shopee")
async def shopee_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive webhook notifications from Shopee
    Events: 0=shop auth, 3=order status update, etc.
    """
    try:
        body = await request.body()
        payload = await request.json()
        
        # Get signature from headers
        signature = request.headers.get("Authorization", "")
        
        # Log webhook
        webhook_log = await run_in_threadpool(
            integration_service.log_webhook,
            db=db,
            platform="shopee",
            event_type=str(payload.get("code")),
            payload=payload,
            headers=dict(request.headers),
            signature=signature,
            ip_address=request.client.host if request.client else None,
        )
        
        # Parse event
        shop_id = str(payload.get("shop_id", ""))
        event_code = payload.get("code")
        
        # Get platform config for this shop
        config = await run_in_threadpool(integration_service.get_platform_config_by_shop, db, "shopee", shop_id)
        
        if config:
            # Verify signature
            client = ShopeeClient(
                app_key=config.app_key,
                app_secret=config.app_secret,
                shop_id=shop_id,
            )
            
            # Event code 3 = order status update
            if event_code == 3:
                order_id = payload.get("data", {}).get("ordersn")
                if order_id:
                    # Process in background
                    background_tasks.add_task(
                        process_order_webhook,
                        db, "shopee", order_id, "order_status_update", str(webhook_log.id)
                    )
        
        return {"code": 0, "message": "OK"}
        
    except Exception as e:
        logger.error(f"Shopee webhook error: {e}")
        return {"code": -1, "message": str(e)}


# ========== Lazada Webhook ==========

@webhook_router.post("/lazada")
async def lazada_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive webhook notifications from Lazada
    Events: ORDER_CREATED, ORDER_STATUS_CHANGED, etc.
    """
    try:
        body = await request.body()
        payload = await request.json()
        
        # Get signature from headers
        signature = request.headers.get("X-Lazada-Sign", "")
        
        # Log webhook
        webhook_log = await run_in_threadpool(
            integration_service.log_webhook,
            db=db,
            platform="lazada",
            event_type=payload.get("message_type", ""),
            payload=payload,
            headers=dict(request.headers),
            signature=signature,
            ip_address=request.client.host if request.client else None,
        )
        
        # Parse event
        message_type = payload.get("message_type", "")
        data = payload.get("data", {})
        
        # Handle order events
        # Lazada message_type can be:
        # - 0: order status update (paid, pending, etc.)
        # - "ORDER_CREATED", "ORDER_STATUS_CHANGED": legacy string types
        order_event_types = ["ORDER_CREATED", "ORDER_STATUS_CHANGED", 0, "0"]
        
        if message_type in order_event_types or str(message_type) in ["0"]:
            order_id = str(data.get("trade_order_id", ""))
            if order_id:
                background_tasks.add_task(
                    process_order_webhook,
                    db, "lazada", order_id, str(message_type), str(webhook_log.id)
                )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Lazada webhook error: {e}")
        return {"success": False, "error": str(e)}


# ========== TikTok Webhook ==========

@webhook_router.post("/tiktok")
async def tiktok_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Receive webhook notifications from TikTok Shop
    Events: ORDER_STATUS_CHANGE, ORDER_CREATE, etc.
    """
    try:
        body = await request.body()
        payload = await request.json()
        
        # Get signature from headers (TikTok uses 'authorization' header)
        signature = request.headers.get("authorization", "") or request.headers.get("X-TT-Signature", "")
        timestamp = request.headers.get("X-TT-Timestamp", "") or request.headers.get("timestamp", "")
        
        # Log webhook
        webhook_log = await run_in_threadpool(
            integration_service.log_webhook,
            db=db,
            platform="tiktok",
            event_type=payload.get("type", ""),
            payload=payload,
            headers=dict(request.headers),
            signature=signature,
            ip_address=request.client.host if request.client else None,
        )
        
        # Parse event
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        shop_id = payload.get("shop_id", "")
        
        # Get platform config for verification
        config = await run_in_threadpool(integration_service.get_platform_config_by_shop, db, "tiktok", shop_id)
        
        if config:
            # Verify signature
            client = TikTokClient(
                app_key=config.app_key,
                app_secret=config.app_secret,
                shop_id=shop_id,
            )
            
            if not client.verify_webhook_signature(body, signature, timestamp):
                logger.error(f"TikTok webhook signature verification failed for shop {shop_id}")
                return {"code": 401, "message": "Invalid signature"}  # Strict Rejection
        
        # Handle order events (numeric: 1=order create, 2=status change, 3=tracking, 11=status update)
        order_event_types = ["ORDER_STATUS_CHANGE", "ORDER_CREATE", "1", "2", "3", "11"]
        if str(event_type) in order_event_types or (isinstance(event_type, int) and event_type in [1, 2, 3, 11]):
            order_id = data.get("order_id", "")
            if order_id:
                background_tasks.add_task(
                    process_order_webhook,
                    db, "tiktok", order_id, str(event_type), str(webhook_log.id)
                )
        
        return {"code": 0, "message": "success"}
        
    except Exception as e:
        logger.error(f"TikTok webhook error: {e}")
        return {"code": -1, "message": str(e)}


# ========== Webhook Status ==========

@webhook_router.get("/status")
def webhook_status():
    """Check webhook endpoints status"""
    return {
        "status": "active",
        "endpoints": {
            "shopee": "/api/webhooks/shopee",
            "lazada": "/api/webhooks/lazada",
            "tiktok": "/api/webhooks/tiktok",
        }
    }
