"""
Label Printing API
Endpoints for logging and querying label prints
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, time, timedelta
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.core import get_db
from app.models.label_log import LabelPrintLog
from app.models import OrderHeader

router = APIRouter(prefix="/labels", tags=["Label Printing"])


# Request/Response Models
class LabelPrintRequest(BaseModel):
    order_ids: List[str]
    platform: str
    batch_id: Optional[str] = None


class LabelPrintBulkRequest(BaseModel):
    """Request to log multiple label prints at once"""
    orders: List[dict]  # [{order_id, external_order_id, platform}]
    batch_id: Optional[str] = None
    printed_by: Optional[str] = None


@router.post("/print-log")
def log_label_print(
    request: LabelPrintRequest,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Log label prints for orders (call this when user prints labels)
    """
    batch_id = request.batch_id or f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now()
    
    created = 0
    skipped = 0
    
    for order_id in request.order_ids:
        # Get order info
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            skipped += 1
            continue
        
        # Check if already logged
        existing = db.query(LabelPrintLog).filter(
            LabelPrintLog.order_id == order.id
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        # Create log entry
        log_entry = LabelPrintLog(
            order_id=order.id,
            external_order_id=order.external_order_id,
            platform=order.channel_code,
            printed_at=now,
            printed_by=UUID(user_id) if user_id else None,
            batch_id=batch_id,
            batch_date=now.date()
        )
        db.add(log_entry)
        created += 1
    
    db.commit()
    
    return {
        "success": True,
        "batch_id": batch_id,
        "created": created,
        "skipped": skipped
    }


@router.get("/daily-summary")
def get_daily_label_summary(
    date: date = Query(..., description="Date to query (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get summary of labels printed on a specific date
    This gives accurate "ยอดแพ็คสินค้าประจำวัน"
    """
    start_dt = datetime.combine(date, time.min)
    end_dt = datetime.combine(date, time.max)
    
    # Query by platform
    results = db.query(
        LabelPrintLog.platform,
        func.count(LabelPrintLog.id).label('count')
    ).filter(
        LabelPrintLog.printed_at >= start_dt,
        LabelPrintLog.printed_at <= end_dt
    ).group_by(LabelPrintLog.platform).all()
    
    platforms = {}
    total = 0
    for platform, count in results:
        platforms[platform] = count
        total += count
    
    return {
        "date": date.isoformat(),
        "total_labels": total,
        "by_platform": platforms
    }


@router.get("/batches")
def get_print_batches(
    date: Optional[date] = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get list of print batches
    """
    query = db.query(
        LabelPrintLog.batch_id,
        LabelPrintLog.batch_date,
        func.count(LabelPrintLog.id).label('count'),
        func.min(LabelPrintLog.printed_at).label('first_print'),
        func.max(LabelPrintLog.printed_at).label('last_print')
    ).group_by(
        LabelPrintLog.batch_id,
        LabelPrintLog.batch_date
    ).order_by(
        func.max(LabelPrintLog.printed_at).desc()
    )
    
    if date:
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        query = query.filter(
            LabelPrintLog.printed_at >= start_dt,
            LabelPrintLog.printed_at <= end_dt
        )
    
    batches = query.limit(limit).all()
    
    return {
        "batches": [
            {
                "batch_id": b.batch_id,
                "date": b.batch_date.isoformat() if b.batch_date else None,
                "count": b.count,
                "first_print": b.first_print.isoformat() if b.first_print else None,
                "last_print": b.last_print.isoformat() if b.last_print else None
            }
            for b in batches
        ]
    }
