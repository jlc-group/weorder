
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
    db: Session = Depends(get_db)
):
    """
    Get summary of items sent out on a specific date
    """
    return ReportService.get_daily_outbound_stats(db, date, str(warehouse_id) if warehouse_id else None)
