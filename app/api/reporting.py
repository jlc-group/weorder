
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from uuid import UUID

from app.core import get_db
from app.services.report_service import ReportService

router = APIRouter(prefix="/report", tags=["Reporting"])

@router.get("/daily-outbound")
def get_daily_outbound(
    date: date = Query(..., description="Date to check (YYYY-MM-DD)"),
    warehouse_id: Optional[UUID] = None,
    date_mode: str = Query("collection", description="Mode: 'collection' (courier pickup) or 'rts' (packing/RTS time)"),
    db: Session = Depends(get_db)
):
    """
    Get summary of items sent out on a specific date
    
    Args:
        date_mode: 
            - 'collection': Uses collection_time (courier pickup time) - default
            - 'rts': Uses rts_time (packing/ready-to-ship time) - matches packing records
    """
    return ReportService.get_daily_outbound_stats(db, date, str(warehouse_id) if warehouse_id else None, date_mode=date_mode)

