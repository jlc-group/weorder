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


@router.get("/sku-summary")
async def get_sku_summary(
    courier: str = Query(..., description="Courier code or ID"),
    status: str = Query("READY_TO_SHIP", description="Order status"),
    channel: Optional[str] = Query(None, description="Platform: tiktok, shopee, lazada, or None for all"),
    db: Session = Depends(get_db),
):
    """
    Get summary of orders grouped by SKU content (for selective printing).
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
    
    # Group by SKU
    sku_groups = {}
    
    for order in orders:
        # Generate hashable group key
        sku_key = get_sku_group(order.items)
        if not sku_key:
            sku_key = "No Items"
            
        if sku_key not in sku_groups:
            sku_groups[sku_key] = {
                "sku_key": sku_key,
                "display_name": sku_key.replace(",", ", "),
                "items": [{"sku": i.sku, "qty": i.quantity, "name": i.product_name} for i in order.items],
                "count": 0,
                "order_ids": []
            }
        
        sku_groups[sku_key]["count"] += 1
        sku_groups[sku_key]["order_ids"].append(order.external_order_id)
        
    # Convert to list and sort by count (desc)
    results = list(sku_groups.values())
    results.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "total_orders": len(orders),
        "groups": results
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
    Generate labels for a batch of orders with SKU preview per file.
    """
    courier = data.get("courier")
    status = data.get("status", "READY_TO_SHIP")
    channel = data.get("channel")
    max_per_file = min(data.get("max_per_file", 50), 100)
    sort_by_sku = data.get("sort_by_sku", True)
    
    # Query orders WITH items for SKU grouping
    query = db.query(OrderHeader).options(
        joinedload(OrderHeader.items)
    ).filter(
        OrderHeader.status_normalized == status
    )
    
    if channel:
        query = query.filter(OrderHeader.channel_code == channel)
    
    if courier:
        query = query.filter(OrderHeader.courier_code.ilike(f"%{courier}%"))
    
    orders = query.all()
    
    if not orders:
        return {"error": "No orders found", "total_orders": 0, "files": []}
    
    # Sort by SKU group if requested
    if sort_by_sku:
        orders_with_group = []
        for order in orders:
            sku_group = get_sku_group(order.items)
            orders_with_group.append({
                "order": order,
                "sku_group": sku_group
            })
        orders_with_group.sort(key=lambda x: x["sku_group"])
        orders = [o["order"] for o in orders_with_group]
    
    # Split into batches and collect SKU preview
    total_orders = len(orders)
    files = []
    
    for page_idx in range(0, total_orders, max_per_file):
        page_orders = orders[page_idx:page_idx + max_per_file]
        page_num = (page_idx // max_per_file) + 1
        
        # Collect SKU counts for this batch
        sku_counts = {}
        for order in page_orders:
            for item in order.items:
                if item.sku:
                    key = item.sku
                    if key not in sku_counts:
                        sku_counts[key] = {
                            "sku": item.sku,
                            "name": item.product_name or item.sku,
                            "qty": 0,
                            "orders": 0
                        }
                    sku_counts[key]["qty"] += item.quantity
                    sku_counts[key]["orders"] += 1
        
        # Sort by quantity (top SKUs first)
        top_skus = sorted(sku_counts.values(), key=lambda x: -x["qty"])[:5]
        
        files.append({
            "page": page_num,
            "orders": len(page_orders),
            "url": f"/api/labels/by-courier?courier={courier or ''}&status={status}&channel={channel or ''}&page={page_num}&per_page={max_per_file}&sort_by_sku={sort_by_sku}",
            "preview": top_skus
        })
    
    return {
        "courier": courier,
        "status": status,
        "channel": channel,
        "total_orders": total_orders,
        "max_per_file": max_per_file,
        "total_files": len(files),
        "files": files
    }

