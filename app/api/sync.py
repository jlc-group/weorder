"""
Sync API - Trigger and monitor order synchronization
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import asyncio
import logging

from app.core.database import get_db
from app.models.sync_log import SyncLog, SyncStatus
from app.services import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)

# Track current running sync (simple in-memory flag)
_current_sync_id: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    message: str
    sync_id: str
    status: str


class SyncStatusResponse(BaseModel):
    is_running: bool
    current_sync_id: Optional[str] = None
    last_sync: Optional[dict] = None


class SyncHistoryItem(BaseModel):
    id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    platform: Optional[str]
    stats: dict
    error_message: Optional[str]

    class Config:
        from_attributes = True


from app.core.database import SessionLocal


# Background sync that properly updates sync log
async def run_sync_background():
    """Background task to run sync with proper status update"""
    global _current_sync_id
    
    db = SessionLocal()
    try:
        # Get the last running sync log
        sync_log = db.query(SyncLog).filter(SyncLog.status == SyncStatus.RUNNING.value).order_by(desc(SyncLog.started_at)).first()
        
        logger.info(f"Starting background sync")
        
        # Run the actual sync
        results = await sync_service.sync_all_platforms(db)
        
        # Calculate totals
        total_fetched = 0
        total_created = 0
        total_updated = 0
        total_errors = 0
        
        for key, result in results.items():
            if result.get("status") == "success":
                total_fetched += result.get("fetched", 0)
                total_created += result.get("created", 0)
                total_updated += result.get("updated", 0)
            else:
                total_errors += 1
        
        # Update sync log
        if sync_log:
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.status = SyncStatus.SUCCESS.value if total_errors == 0 else SyncStatus.FAILED.value
            sync_log.stats = {
                "fetched": total_fetched,
                "created": total_created,
                "updated": total_updated,
                "errors": total_errors,
                "details": results
            }
            db.commit()
            logger.info(f"Sync completed: fetched={total_fetched}, created={total_created}, updated={total_updated}")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
        # Update sync log with error
        sync_log = db.query(SyncLog).filter(SyncLog.status == SyncStatus.RUNNING.value).order_by(desc(SyncLog.started_at)).first()
        if sync_log:
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.status = SyncStatus.FAILED.value
            sync_log.error_message = str(e)[:500]
            db.commit()
    
    finally:
        _current_sync_id = None
        db.close()


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a full sync for all platforms.
    Returns immediately while sync runs in background.
    """
    global _current_sync_id
    
    # Check if sync is already running (naive check)
    if _current_sync_id:
        # Check if actually running in DB log? 
        # For now, just warn but allow over-ride if stale
        pass 
        
    # Generate ID
    import uuid
    sync_id = str(uuid.uuid4())
    _current_sync_id = sync_id
    
    # Create sync log entry
    sync_log = SyncLog(
        started_at=datetime.now(timezone.utc),
        status=SyncStatus.RUNNING.value,
        platform=None,  # All platforms
        stats={}
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    
    # Use wrapper to run in background with FRESH session
    background_tasks.add_task(run_sync_background)
    
    return SyncTriggerResponse(
        message="Sync started",
        sync_id=str(sync_log.id), # Use DB ID
        status="running"
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Get current sync status and last sync info.
    Uses DB-based check instead of in-memory flag for reliability.
    """
    from datetime import timedelta
    
    # Get last sync
    last_sync = db.query(SyncLog).order_by(desc(SyncLog.started_at)).first()
    
    # Check for RUNNING syncs in DB (more reliable than in-memory flag)
    running_sync = db.query(SyncLog).filter(
        SyncLog.status == SyncStatus.RUNNING.value
    ).order_by(desc(SyncLog.started_at)).first()
    
    # Auto-expire stuck syncs older than 10 minutes (reduced from 30)
    if running_sync:
        sync_started = running_sync.started_at
        if sync_started.tzinfo is None:
            sync_started = sync_started.replace(tzinfo=timezone.utc)
        
        age = datetime.now(timezone.utc) - sync_started
        if age > timedelta(minutes=10):
            # Mark as failed - stuck too long
            running_sync.status = SyncStatus.FAILED.value
            running_sync.completed_at = datetime.now(timezone.utc)
            running_sync.error_message = "Auto-expired: stuck for over 10 minutes"
            db.commit()
            running_sync = None
            logger.warning("Auto-expired stuck sync job")
    
    last_sync_info = None
    if last_sync:
        last_sync_info = {
            "id": str(last_sync.id),
            "started_at": last_sync.started_at.isoformat() if last_sync.started_at else None,
            "completed_at": last_sync.completed_at.isoformat() if last_sync.completed_at else None,
            "status": last_sync.status,
            "stats": last_sync.stats or {}
        }
    
    return SyncStatusResponse(
        is_running=running_sync is not None,
        current_sync_id=str(running_sync.id) if running_sync else None,
        last_sync=last_sync_info
    )


@router.get("/history")
async def get_sync_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent sync history.
    """
    logs = db.query(SyncLog).order_by(desc(SyncLog.started_at)).limit(limit).all()
    
    return [
        {
            "id": str(log.id),
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "status": log.status,
            "platform": log.platform,
            "stats": log.stats or {},
            "error_message": log.error_message
        }
        for log in logs
    ]


@router.post("/reset")
async def reset_stuck_sync(db: Session = Depends(get_db)):
    """
    Force reset any stuck sync jobs.
    Use this when sync is stuck in 'running' state.
    """
    global _current_sync_id
    
    # Find all running syncs
    running_syncs = db.query(SyncLog).filter(
        SyncLog.status == SyncStatus.RUNNING.value
    ).all()
    
    reset_count = 0
    for sync in running_syncs:
        sync.status = SyncStatus.FAILED.value
        sync.completed_at = datetime.now(timezone.utc)
        sync.error_message = "Force reset by user"
        reset_count += 1
    
    # Clear in-memory flag
    _current_sync_id = None
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reset {reset_count} stuck sync job(s)",
        "reset_count": reset_count
    }

@router.post("/pending")
async def sync_pending_orders(
    db: Session = Depends(get_db)
):
    """
    Sync ALL pending orders from TikTok (orders waiting to be shipped).
    Uses status filter instead of time range to catch old pending orders.
    """
    from app.models.integration import PlatformConfig
    from app.integrations.tiktok import TikTokClient
    from app.services.sync_service import OrderSyncService
    from app.models.master import Company
    from datetime import datetime, timedelta
    
    # Get TikTok config
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == 'tiktok',
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        return {"error": "No active TikTok configuration"}
    
    # Get company
    company = db.query(Company).first()
    if not company:
        return {"error": "No company configured"}
    
    # Initialize client
    client = TikTokClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    
    # Initialize sync service
    service = OrderSyncService(db)
    
    stats = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "errors": 0
    }
    
    # Fetch orders by status (no time limit!)
    # TikTok API supports filtering by status: AWAITING_SHIPMENT, AWAITING_COLLECTION
    statuses_to_sync = ['AWAITING_SHIPMENT', 'AWAITING_COLLECTION']
    
    for status in statuses_to_sync:
        cursor = None
        has_more = True
        page = 0
        
        while has_more:
            page += 1
            try:
                # Get orders with status filter (no time range = all pending)
                result = await client.get_orders(
                    status=status,
                    cursor=cursor,
                    page_size=100,
                    use_update_time=False  # Don't use time filter
                )
                
                orders = result.get("orders", [])
                cursor = result.get("next_cursor")
                has_more = result.get("has_more", False) and cursor
                
                stats["fetched"] += len(orders)
                
                # Process each order
                for raw_order in orders:
                    try:
                        # Normalize order
                        normalized = client.normalize_order(raw_order)
                        if normalized:
                            created, updated = await service._process_order(normalized, company.id)
                            if created:
                                stats["created"] += 1
                            elif updated:
                                stats["updated"] += 1
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(f"Error processing order: {e}")
                
                # Commit after each page
                db.commit()
                
            except Exception as e:
                logger.error(f"Error fetching {status} orders page {page}: {e}")
                stats["errors"] += 1
                break
    
    return {
        "message": "Pending orders sync completed",
        "stats": stats
    }

