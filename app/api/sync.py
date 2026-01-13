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


async def run_sync_background(db_factory, sync_id: str):
    """Background task to run sync"""
    global _current_sync_id
    
    db = db_factory()
    try:
        # Get sync log record
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_id).first()
        if not sync_log:
            logger.error(f"Sync log not found: {sync_id}")
            return
        
        logger.info(f"Starting background sync: {sync_id}")
        
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
        
        logger.info(f"Sync completed: {sync_id} - fetched={total_fetched}, created={total_created}")
        
    except Exception as e:
        logger.error(f"Sync failed: {sync_id} - {e}")
        
        # Update sync log with error
        sync_log = db.query(SyncLog).filter(SyncLog.id == sync_id).first()
        if sync_log:
            sync_log.completed_at = datetime.now(timezone.utc)
            sync_log.status = SyncStatus.FAILED.value
            sync_log.error_message = str(e)[:500]
            db.commit()
    
    finally:
        _current_sync_id = None
        db.close()


from app.core.database import SessionLocal

# Wrapper to ensure fresh DB session for background task
async def run_sync_background():
    db = SessionLocal()
    try:
        await sync_service.sync_all_platforms(db)
    finally:
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
    """
    global _current_sync_id
    
    # Get last sync
    last_sync = db.query(SyncLog).order_by(desc(SyncLog.started_at)).first()
    
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
        is_running=_current_sync_id is not None,
        current_sync_id=_current_sync_id,
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
