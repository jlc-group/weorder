"""
Packing API - Batch/Wave management for packing operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone, date
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.packing_batch import PackingBatch, PackingBatchOrder
from app.models.order import OrderHeader
from app.models.integration import PlatformConfig

router = APIRouter(prefix="/packing", tags=["Packing"])
logger = logging.getLogger(__name__)


# ============ Schemas ============

class SyncResponse(BaseModel):
    message: str
    synced_at: str
    orders_synced: int
    new_orders: int

class BatchCreateRequest(BaseModel):
    platform: Optional[str] = None  # tiktok, shopee, lazada, or None for all
    notes: Optional[str] = None

class BatchResponse(BaseModel):
    id: str
    batch_number: int
    batch_date: str
    synced_at: Optional[str]
    cutoff_at: str
    order_count: int
    packed_count: int
    printed_count: int
    status: str
    platform: Optional[str]
    notes: Optional[str]

class BatchListResponse(BaseModel):
    batches: List[BatchResponse]
    total: int


# ============ Endpoints ============

@router.post("/sync", response_model=SyncResponse)
async def sync_orders_for_packing(
    platform: Optional[str] = Query(None, description="Platform to sync: tiktok, shopee, lazada"),
    db: Session = Depends(get_db)
):
    """
    Sync pending orders from marketplace(s) for packing.
    Call this before creating a batch to get latest orders.
    """
    from app.integrations.tiktok import TikTokClient
    from app.services.sync_service import OrderSyncService
    from app.models.master import Company
    
    synced_at = datetime.now(timezone.utc)
    total_synced = 0
    new_orders = 0
    
    # Get configs
    query = db.query(PlatformConfig).filter(PlatformConfig.is_active == True)
    if platform:
        query = query.filter(PlatformConfig.platform == platform)
    configs = query.all()
    
    if not configs:
        raise HTTPException(status_code=400, detail=f"No active platform config found")
    
    # Get company
    company = db.query(Company).first()
    if not company:
        raise HTTPException(status_code=400, detail="No company configured")
    
    service = OrderSyncService(db)
    
    for config in configs:
        if config.platform == 'tiktok':
            try:
                client = TikTokClient(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    shop_id=config.shop_id,
                    access_token=config.access_token,
                    refresh_token=config.refresh_token
                )
                
                # Sync pending orders by status
                for status in ['AWAITING_SHIPMENT', 'AWAITING_COLLECTION']:
                    cursor = None
                    has_more = True
                    
                    while has_more:
                        result = await client.get_orders(
                            status=status,
                            cursor=cursor,
                            page_size=100
                        )
                        
                        orders = result.get("orders", [])
                        cursor = result.get("next_cursor")
                        has_more = result.get("has_more", False) and cursor
                        
                        total_synced += len(orders)
                        
                        for raw_order in orders:
                            try:
                                normalized = client.normalize_order(raw_order)
                                if normalized:
                                    created, updated = await service._process_order(normalized, company.id)
                                    if created:
                                        new_orders += 1
                            except Exception as e:
                                logger.error(f"Error processing order: {e}")
                        
                        db.commit()
                        
            except Exception as e:
                logger.error(f"Error syncing {config.platform}: {e}")
    
    return SyncResponse(
        message="Sync completed",
        synced_at=synced_at.isoformat(),
        orders_synced=total_synced,
        new_orders=new_orders
    )


@router.post("/batch", response_model=BatchResponse)
async def create_packing_batch(
    request: BatchCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new packing batch (cutoff).
    This captures all pending orders at the current time.
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    
    # Get next batch number for today
    last_batch = db.query(PackingBatch).filter(
        func.date(PackingBatch.batch_date) == today
    ).order_by(desc(PackingBatch.batch_number)).first()
    
    batch_number = (last_batch.batch_number + 1) if last_batch else 1
    
    # Get pending orders not in any batch
    order_query = db.query(OrderHeader).filter(
        OrderHeader.status_normalized.in_(['PAID', 'READY_TO_SHIP']),
        ~OrderHeader.id.in_(
            db.query(PackingBatchOrder.order_id)
        )
    )
    
    if request.platform:
        order_query = order_query.filter(OrderHeader.channel_code == request.platform)
    
    pending_orders = order_query.all()
    
    # Create batch
    batch = PackingBatch(
        batch_number=batch_number,
        batch_date=now,
        synced_at=now,
        cutoff_at=now,
        order_count=len(pending_orders),
        status="PENDING",
        platform=request.platform,
        notes=request.notes
    )
    db.add(batch)
    db.flush()
    
    # Add orders to batch
    for seq, order in enumerate(pending_orders, 1):
        batch_order = PackingBatchOrder(
            batch_id=batch.id,
            order_id=order.id,
            sequence=seq
        )
        db.add(batch_order)
    
    db.commit()
    db.refresh(batch)
    
    return BatchResponse(
        id=str(batch.id),
        batch_number=batch.batch_number,
        batch_date=batch.batch_date.date().isoformat(),
        synced_at=batch.synced_at.isoformat() if batch.synced_at else None,
        cutoff_at=batch.cutoff_at.isoformat(),
        order_count=batch.order_count,
        packed_count=batch.packed_count,
        printed_count=batch.printed_count,
        status=batch.status,
        platform=batch.platform,
        notes=batch.notes
    )


@router.get("/batches", response_model=BatchListResponse)
async def list_packing_batches(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List packing batches.
    """
    query = db.query(PackingBatch)
    
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(func.date(PackingBatch.batch_date) == filter_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    if status:
        query = query.filter(PackingBatch.status == status)
    
    total = query.count()
    batches = query.order_by(desc(PackingBatch.cutoff_at)).limit(limit).all()
    
    return BatchListResponse(
        batches=[
            BatchResponse(
                id=str(b.id),
                batch_number=b.batch_number,
                batch_date=b.batch_date.date().isoformat(),
                synced_at=b.synced_at.isoformat() if b.synced_at else None,
                cutoff_at=b.cutoff_at.isoformat(),
                order_count=b.order_count,
                packed_count=b.packed_count,
                printed_count=b.printed_count,
                status=b.status,
                platform=b.platform,
                notes=b.notes
            )
            for b in batches
        ],
        total=total
    )


@router.get("/batch/{batch_id}")
async def get_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    Get batch details with orders.
    """
    batch = db.query(PackingBatch).filter(PackingBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Get orders in batch
    batch_orders = db.query(PackingBatchOrder, OrderHeader).join(
        OrderHeader, PackingBatchOrder.order_id == OrderHeader.id
    ).filter(
        PackingBatchOrder.batch_id == batch_id
    ).order_by(PackingBatchOrder.sequence).all()
    
    return {
        "id": str(batch.id),
        "batch_number": batch.batch_number,
        "batch_date": batch.batch_date.date().isoformat(),
        "synced_at": batch.synced_at.isoformat() if batch.synced_at else None,
        "cutoff_at": batch.cutoff_at.isoformat(),
        "order_count": batch.order_count,
        "packed_count": batch.packed_count,
        "printed_count": batch.printed_count,
        "status": batch.status,
        "platform": batch.platform,
        "notes": batch.notes,
        "orders": [
            {
                "sequence": bo.sequence,
                "order_id": str(oh.id),
                "external_id": oh.external_order_id,
                "customer": oh.customer_name,
                "total": float(oh.total_amount) if oh.total_amount else 0,
                "is_packed": bo.is_packed,
                "is_printed": bo.is_printed,
                "status": oh.status_normalized
            }
            for bo, oh in batch_orders
        ]
    }


@router.get("/pending-count")
async def get_pending_order_count(
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get count of pending orders not yet in any batch.
    """
    query = db.query(func.count(OrderHeader.id)).filter(
        OrderHeader.status_normalized.in_(['PAID', 'READY_TO_SHIP']),
        ~OrderHeader.id.in_(
            db.query(PackingBatchOrder.order_id)
        )
    )
    
    if platform:
        query = query.filter(OrderHeader.channel_code == platform)
    
    count = query.scalar()
    
    # Get last sync time
    last_order = db.query(OrderHeader).filter(
        OrderHeader.channel_code == (platform or 'tiktok')
    ).order_by(desc(OrderHeader.created_at)).first()
    
    return {
        "pending_count": count,
        "last_sync": last_order.created_at.isoformat() if last_order and last_order.created_at else None
    }
