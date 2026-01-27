"""
Courier-Separated Labels API
Provides endpoints for generating labels separated by courier (J&T, Flash Express, etc.)
with SKU grouping for efficient packing workflow
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional, List, Dict
import io
import logging

from app.core.database import get_db
from app.models import OrderHeader, OrderItem
from app.services.label_service import LabelService

router = APIRouter(prefix="/labels", tags=["Labels"])
logger = logging.getLogger(__name__)

# TikTok Courier IDs (from your script)
COURIER_MAP = {
    "6841743441349706241": {"name": "J&T Express", "code": "jt"},
    "7099697896546633478": {"name": "Flash Express", "code": "flash"},
    "7341219504757458694": {"name": "Kerry Express", "code": "kerry"},
    "7099697889416388870": {"name": "Thailand Post", "code": "thaipost"},
}


def get_sku_group(items: List) -> str:
    """Generate SKU group string for sorting (same as your script)"""
    sorted_items = sorted(items, key=lambda x: x.sku or "")
    return ",".join([f"{item.sku}={item.quantity}" for item in sorted_items if item.sku])


@router.get("/platform-summary")
async def get_platform_summary(
    status: str = Query("READY_TO_SHIP", description="Order status to filter"),
    db: Session = Depends(get_db),
):
    """
    Get summary of orders by platform for label printing.
    
    Returns count per platform (TikTok, Shopee, Lazada).
    """
    query = db.query(
        OrderHeader.channel_code,
        func.count(OrderHeader.id).label("count")
    ).filter(
        OrderHeader.status_normalized == status
    ).group_by(OrderHeader.channel_code)
    
    results = query.all()
    
    platforms = []
    total = 0
    
    for channel_code, count in results:
        platforms.append({
            "channel": channel_code or "unknown",
            "channel_name": (channel_code or "unknown").title(),
            "count": count
        })
        total += count
    
    return {
        "status": status,
        "total": total,
        "platforms": sorted(platforms, key=lambda x: x["count"], reverse=True)
    }


@router.get("/courier-summary")
async def get_courier_summary(
    status: str = Query("READY_TO_SHIP", description="Order status to filter"),
    channel: Optional[str] = Query(None, description="Platform: tiktok, shopee, lazada, or None for all"),
    db: Session = Depends(get_db),
):
    """
    Get summary of orders by courier for label printing.
    
    Returns count per courier for preparation.
    """
    # Query orders with courier info
    query = db.query(
        OrderHeader.courier_code,
        func.count(OrderHeader.id).label("count")
    ).filter(
        OrderHeader.status_normalized == status
    )
    
    if channel:
        query = query.filter(OrderHeader.channel_code == channel)
    
    query = query.group_by(OrderHeader.courier_code)
    
    results = query.all()
    
    couriers = []
    total = 0
    
    for courier_code, count in results:
        courier_name = courier_code or "Unknown"
        
        # Try to match known courier IDs
        for courier_id, info in COURIER_MAP.items():
            if courier_id in (courier_code or ""):
                courier_name = info["name"]
                break
        
        couriers.append({
            "courier_code": courier_code or "unknown",
            "courier_name": courier_name,
            "count": count
        })
        total += count
    
    return {
        "status": status,
        "channel": channel or "all",
        "total": total,
        "couriers": couriers
    }


@router.get("/by-courier")
async def get_labels_by_courier(
    courier: str = Query(..., description="Courier code or ID"),
    status: str = Query("READY_TO_SHIP", description="Order status"),
    channel: Optional[str] = Query(None, description="Platform: tiktok, shopee, lazada, or None for all"),
    sort_by_sku: bool = Query(True, description="Sort by SKU group"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100, description="Max 100 per batch, default 50 for reliability"),
    db: Session = Depends(get_db),
):
    """
    Get label PDF for specific courier, sorted by SKU group.
    
    - Labels are sorted by SKU group (same items together)
    - Max 100 labels per request (split for large batches)
    - Returns PDF file
    """
    # Query orders for this courier (with eager loading for items)
    query = db.query(OrderHeader).options(
        joinedload(OrderHeader.items)
    ).filter(
        OrderHeader.status_normalized == status
    )
    
    # Filter by channel if specified
    if channel:
        query = query.filter(OrderHeader.channel_code == channel)
    
    # Filter by courier (partial match for flexibility)
    if courier and courier != "all":
        query = query.filter(OrderHeader.courier_code.ilike(f"%{courier}%"))
    
    orders = query.all()
    
    if not orders:
        return JSONResponse(
            status_code=404,
            content={"error": f"No orders found for courier: {courier}"}
        )
    
    # Add SKU group and sort
    orders_with_group = []
    for order in orders:
        sku_group = get_sku_group(order.items)
        orders_with_group.append({
            "order": order,
            "sku_group": sku_group,
            "external_id": order.external_order_id
        })
    
    if sort_by_sku:
        orders_with_group.sort(key=lambda x: x["sku_group"])
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_orders = orders_with_group[start:end]
    
    if not page_orders:
        return JSONResponse(
            status_code=404,
            content={"error": f"No orders on page {page}"}
        )
    
    # Get order IDs for label generation
    order_ids = [o["external_id"] for o in page_orders]
    
    # Generate PDF
    try:
        pdf_bytes = await LabelService.generate_batch_labels(db, order_ids)
        
        if not pdf_bytes:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to generate labels - no PDF returned"}
            )
        
        # Filename with courier and page info
        courier_name = courier.replace(" ", "_")
        date_str = datetime.now().strftime("%d%m%Y")
        total_pages = (len(orders_with_group) + per_page - 1) // per_page
        
        filename = f"{courier_name}_{date_str}_page{page}of{total_pages}_{len(page_orders)}labels.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Total-Orders": str(len(orders_with_group)),
                "X-Page": str(page),
                "X-Total-Pages": str(total_pages),
                "X-Orders-This-Page": str(len(page_orders))
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating labels: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/sku-summary")
async def get_sku_packing_summary(
    status: str = Query("READY_TO_SHIP", description="Order status"),
    channel: str = Query("tiktok", description="Platform"),
    courier: Optional[str] = Query(None, description="Filter by courier"),
    db: Session = Depends(get_db),
):
    """
    Get SKU summary for packing preparation (like count_item_group in your script).
    
    Groups orders by identical SKU combinations for efficient picking.
    """
    # Query orders (with eager loading for items)
    query = db.query(OrderHeader).options(
        joinedload(OrderHeader.items)
    ).filter(
        OrderHeader.status_normalized == status,
        OrderHeader.channel_code == channel
    )
    
    if courier:
        query = query.filter(OrderHeader.courier_code.ilike(f"%{courier}%"))
    
    orders = query.all()
    
    # Group by SKU combination
    sku_groups: Dict[str, dict] = {}
    
    for order in orders:
        sku_group = get_sku_group(order.items)
        
        if sku_group not in sku_groups:
            sku_groups[sku_group] = {
                "sku_group": sku_group,
                "items": [{"sku": item.sku, "qty": item.quantity} for item in order.items if item.sku],
                "order_count": 0,
                "order_ids": []
            }
        
        sku_groups[sku_group]["order_count"] += 1
        sku_groups[sku_group]["order_ids"].append(order.external_order_id)
    
    # Sort by item name (like your script)
    sorted_groups = sorted(
        sku_groups.values(),
        key=lambda x: " ".join([i["sku"] for i in x["items"]])
    )
    
    return {
        "status": status,
        "channel": channel,
        "courier": courier,
        "total_orders": len(orders),
        "unique_sku_groups": len(sorted_groups),
        "groups": sorted_groups
    }


@router.post("/print-batch")
async def print_batch_labels(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Generate labels for a batch of orders.
    
    Input:
    {
        "courier": "J&T Express",
        "status": "READY_TO_SHIP",
        "channel": "tiktok",
        "max_per_file": 100,  // Split into multiple files
        "sort_by_sku": true
    }
    
    Returns: Summary with download links
    """
    courier = data.get("courier")
    status = data.get("status", "READY_TO_SHIP")
    channel = data.get("channel", "tiktok")
    max_per_file = min(data.get("max_per_file", 100), 100)
    sort_by_sku = data.get("sort_by_sku", True)
    
    # Query orders
    query = db.query(OrderHeader).filter(
        OrderHeader.status_normalized == status,
        OrderHeader.channel_code == channel
    )
    
    if courier:
        query = query.filter(OrderHeader.courier_code.ilike(f"%{courier}%"))
    
    orders = query.all()
    
    if not orders:
        return {"error": "No orders found", "total": 0}
    
    # Calculate batches
    total_orders = len(orders)
    total_pages = (total_orders + max_per_file - 1) // max_per_file
    
    return {
        "courier": courier,
        "status": status,
        "channel": channel,
        "total_orders": total_orders,
        "max_per_file": max_per_file,
        "total_files": total_pages,
        "files": [
            {
                "page": i + 1,
                "url": f"/api/labels/by-courier?courier={courier}&status={status}&channel={channel}&page={i+1}&per_page={max_per_file}&sort_by_sku={sort_by_sku}",
                "orders": min(max_per_file, total_orders - (i * max_per_file))
            }
            for i in range(total_pages)
        ]
    }
