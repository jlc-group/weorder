"""
Reconciliation API - Endpoints for data integrity checks
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.core import get_db
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.get("/health")
def get_sync_health(db: Session = Depends(get_db)):
    """
    Get overall sync health dashboard data
    Shows status of each platform and any issues detected
    """
    return ReconciliationService.get_health_dashboard(db)


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db)):
    """
    Get last sync status for each platform
    """
    return ReconciliationService.get_sync_status(db)


@router.get("/daily-summary")
def get_daily_summary(
    date: date = Query(default=None, description="Date to check (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get order summary for a specific date from WeOrder database
    """
    target_date = date or datetime.now().date()
    return {
        "date": target_date.isoformat(),
        "summary": ReconciliationService.get_daily_summary(db, target_date)
    }


@router.get("/gaps")
def get_data_gaps(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to check"),
    db: Session = Depends(get_db)
):
    """
    Check for data gaps or anomalies in recent order data
    """
    return ReconciliationService.get_recent_gaps(db, days)


@router.get("/compare/{platform}")
async def compare_with_marketplace(
    platform: str,
    date: date = Query(..., description="Date to compare (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Compare WeOrder orders with Marketplace API for a specific date
    Returns missing orders and match rate
    """
    if platform not in ['tiktok', 'shopee', 'lazada']:
        return {"error": f"Invalid platform: {platform}"}
    
    return await ReconciliationService.compare_with_marketplace(db, platform, date)


@router.get("/live-compare/tiktok")
async def live_compare_tiktok(
    db: Session = Depends(get_db)
):
    """
    Live comparison: Show WeOrder TikTok data and attempt TikTok API comparison
    Returns status counts from both systems
    """
    from app.models.integration import PlatformConfig
    from app.models.order import OrderHeader
    from datetime import datetime
    from sqlalchemy import func
    
    # Get WeOrder counts by status for today
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    
    weorder_counts = {}
    results = db.query(
        OrderHeader.status_normalized,
        func.count(OrderHeader.id)
    ).filter(
        OrderHeader.channel_code == 'tiktok',
        OrderHeader.order_datetime >= start_of_day
    ).group_by(OrderHeader.status_normalized).all()
    
    for status, count in results:
        weorder_counts[status] = count
    
    weorder_total = sum(weorder_counts.values())
    
    # Try to get TikTok config
    channel = db.query(PlatformConfig).filter(
        PlatformConfig.platform == 'tiktok',
        PlatformConfig.is_active == True
    ).first()
    
    response = {
        "date": today.isoformat(),
        "weorder": {
            "total": weorder_total,
            "by_status": weorder_counts
        }
    }
    
    if not channel:
        response["tiktok_api"] = {"error": "No active TikTok channel configured"}
        return response
    
    # Try to call TikTok API
    try:
        from app.integrations.tiktok import TikTokClient
        
        client = TikTokClient(
            app_key=channel.app_key,
            app_secret=channel.app_secret,
            shop_id=channel.shop_id,
            access_token=channel.access_token,
            refresh_token=channel.refresh_token
        )
        
        # Get orders from TikTok (today)
        tiktok_data = await client.get_orders(
            time_from=start_of_day,
            time_to=datetime.now()
        )
        
        tiktok_total = tiktok_data.get('total', 0)
        tiktok_orders = tiktok_data.get('orders', [])
        
        # Count by status from TikTok
        tiktok_counts = {}
        for order in tiktok_orders:
            status = order.get('status', 'UNKNOWN')
            tiktok_counts[status] = tiktok_counts.get(status, 0) + 1
        
        # Calculate difference
        difference = tiktok_total - weorder_total
        match_rate = round(weorder_total / max(tiktok_total, 1) * 100, 1)
        
        response["tiktok_api"] = {
            "total": tiktok_total,
            "fetched_count": len(tiktok_orders),
            "by_status": tiktok_counts
        }
        response["comparison"] = {
            "difference": difference,
            "match_rate": match_rate,
            "status": "ok" if difference == 0 else ("warning" if abs(difference) < 10 else "critical")
        }
        
    except Exception as e:
        import traceback
        response["tiktok_api"] = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    return response
