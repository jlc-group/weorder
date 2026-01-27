"""
TikTok Affiliate & GMV API Endpoints
Provides endpoints for:
- Video GMV / Live GMV breakdown
- Creator/Affiliate statistics
- Creative count by SKU
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.database import get_db
from app.integrations.tiktok import TikTokClient
from app.models.integration import PlatformConfig

router = APIRouter()


async def get_tiktok_client(db: Session):
    """Get configured TikTok client from database config"""
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == 'tiktok',
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="No active TikTok configuration found")
    
    return TikTokClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token,
    )


@router.get("/gmv-breakdown")
async def get_gmv_breakdown(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_db),
):
    """
    Get TikTok GMV breakdown by content type
    
    Returns:
    - video_gmv: ยอดขายจากวิดีโอ
    - live_gmv: ยอดขายจาก live
    - showcase_gmv: ยอดขายจาก showcase  
    - direct_gmv: ยอดขายตรง
    - affiliate_commission: ค่าคอมมิชชั่น creator
    """
    client = await get_tiktok_client(db)
    
    time_to = datetime.now(timezone.utc)
    time_from = time_to - timedelta(days=days)
    
    try:
        result = await client.get_gmv_breakdown(time_from, time_to)
        return {
            "success": True,
            "period": {
                "from": time_from.isoformat(),
                "to": time_to.isoformat(),
                "days": days
            },
            "data": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/affiliate-orders") 
async def get_affiliate_orders(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get TikTok affiliate orders (orders from creator content)
    
    Returns orders with content_type (VIDEO, LIVE, SHOWCASE)
    """
    client = await get_tiktok_client(db)
    
    time_to = datetime.now(timezone.utc)
    time_from = time_to - timedelta(days=days)
    
    try:
        result = await client.get_affiliate_orders(time_from, time_to, page_size=limit)
        return {
            "success": True,
            "period": {
                "from": time_from.isoformat(),
                "to": time_to.isoformat(),
            },
            "orders": result.get("orders", []),
            "total": len(result.get("orders", [])),
            "next_cursor": result.get("next_page_token")
        }
    except Exception as e:
        return {"success": False, "error": str(e), "orders": []}


@router.get("/creators")
async def get_affiliate_creators(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Get list of affiliate creators promoting our products
    """
    client = await get_tiktok_client(db)
    
    try:
        result = await client.get_affiliate_creators(page_size=limit)
        return {
            "success": True,
            "creators": result.get("creators", []),
            "total": len(result.get("creators", [])),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "creators": []}


@router.get("/creators/{creator_id}/performance")
async def get_creator_performance(
    creator_id: str,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Get performance statistics for a specific creator
    
    Returns video_gmv, live_gmv, commission earned
    """
    client = await get_tiktok_client(db)
    
    try:
        result = await client.get_creator_performance(creator_id, days)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/sku-creative-count")
async def get_sku_creative_count(db: Session = Depends(get_db)):
    """
    Get creative count grouped by SKU (last 30 days)
    
    Returns: {sku: {video_count, live_count, total_orders}}
    """
    client = await get_tiktok_client(db)
    
    try:
        result = await client.get_sku_creative_count()
        return {
            "success": True,
            "sku_count": len(result),
            "data": result
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}


@router.get("/products/{product_id}/creatives")
async def get_product_creatives(
    product_id: str,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Get creatives (video/live content) for a specific product
    """
    client = await get_tiktok_client(db)
    
    try:
        result = await client.get_product_creatives(product_id, page_size=limit)
        return {
            "success": True,
            "creatives": result.get("creatives", []),
            "total": len(result.get("creatives", []))
        }
    except Exception as e:
        return {"success": False, "error": str(e), "creatives": []}
