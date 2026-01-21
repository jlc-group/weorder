"""
Manifest API Router - ใบส่งสินค้ารวม
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import logging

from app.core.database import get_db
from app.models import OrderHeader
from app.models.manifest import Manifest, ManifestItem, ManifestStatus

logger = logging.getLogger(__name__)

manifest_router = APIRouter(prefix="/manifests", tags=["manifests"])


class CreateManifestRequest(BaseModel):
    platform: Optional[str] = None
    courier: Optional[str] = None
    notes: Optional[str] = None


class AddOrdersRequest(BaseModel):
    order_ids: List[str]


@manifest_router.get("")
def list_manifests(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all manifests"""
    query = db.query(Manifest).order_by(Manifest.created_at.desc())
    
    if status:
        query = query.filter(Manifest.status == status)
    
    manifests = query.limit(limit).all()
    
    return {
        "manifests": [
            {
                "id": str(m.id),
                "manifest_number": m.manifest_number,
                "platform": m.platform,
                "courier": m.courier,
                "status": m.status.value if m.status else None,
                "order_count": m.order_count,
                "parcel_count": m.parcel_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "closed_at": m.closed_at.isoformat() if m.closed_at else None,
            }
            for m in manifests
        ],
        "count": len(manifests)
    }


@manifest_router.post("")
def create_manifest(
    request: CreateManifestRequest,
    db: Session = Depends(get_db)
):
    """Create a new manifest"""
    manifest = Manifest(
        platform=request.platform,
        courier=request.courier,
        notes=request.notes,
        status=ManifestStatus.OPEN,
    )
    manifest.manifest_number = manifest.generate_manifest_number()
    
    db.add(manifest)
    db.commit()
    db.refresh(manifest)
    
    return {
        "success": True,
        "manifest_id": str(manifest.id),
        "manifest_number": manifest.manifest_number,
        "message": f"Created manifest {manifest.manifest_number}"
    }


@manifest_router.get("/{manifest_id}")
def get_manifest(
    manifest_id: str,
    db: Session = Depends(get_db)
):
    """Get manifest details with items"""
    try:
        manifest_uuid = UUID(manifest_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid manifest ID")
    
    manifest = db.query(Manifest).filter(Manifest.id == manifest_uuid).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    return {
        "id": str(manifest.id),
        "manifest_number": manifest.manifest_number,
        "platform": manifest.platform,
        "courier": manifest.courier,
        "status": manifest.status.value if manifest.status else None,
        "order_count": manifest.order_count,
        "parcel_count": manifest.parcel_count,
        "notes": manifest.notes,
        "created_at": manifest.created_at.isoformat() if manifest.created_at else None,
        "closed_at": manifest.closed_at.isoformat() if manifest.closed_at else None,
        "picked_up_at": manifest.picked_up_at.isoformat() if manifest.picked_up_at else None,
        "items": [
            {
                "id": str(item.id),
                "order_id": str(item.order_id),
                "external_order_id": item.external_order_id,
                "tracking_number": item.tracking_number,
                "customer_name": item.customer_name,
                "added_at": item.added_at.isoformat() if item.added_at else None,
            }
            for item in manifest.items
        ]
    }


@manifest_router.post("/{manifest_id}/add-orders")
def add_orders_to_manifest(
    manifest_id: str,
    request: AddOrdersRequest,
    db: Session = Depends(get_db)
):
    """Add orders to manifest"""
    try:
        manifest_uuid = UUID(manifest_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid manifest ID")
    
    manifest = db.query(Manifest).filter(Manifest.id == manifest_uuid).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    if manifest.status != ManifestStatus.OPEN:
        raise HTTPException(status_code=400, detail="Manifest is not open")
    
    added = 0
    skipped = 0
    
    for order_id_str in request.order_ids:
        try:
            order_uuid = UUID(order_id_str)
            
            # Check if already in manifest
            existing = db.query(ManifestItem).filter(
                ManifestItem.manifest_id == manifest_uuid,
                ManifestItem.order_id == order_uuid
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Get order details
            order = db.query(OrderHeader).filter(OrderHeader.id == order_uuid).first()
            if not order:
                continue
            
            # Add to manifest
            item = ManifestItem(
                manifest_id=manifest_uuid,
                order_id=order_uuid,
                external_order_id=order.external_order_id,
                tracking_number=order.tracking_number,
                customer_name=order.customer_name,
            )
            db.add(item)
            added += 1
            
        except Exception as e:
            logger.error(f"Error adding order {order_id_str}: {e}")
            continue
    
    # Update counts
    manifest.order_count = len(manifest.items) + added
    manifest.parcel_count = manifest.order_count  # 1:1 for now
    
    db.commit()
    
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "total_orders": manifest.order_count,
        "message": f"Added {added} orders to manifest"
    }


@manifest_router.post("/{manifest_id}/close")
def close_manifest(
    manifest_id: str,
    db: Session = Depends(get_db)
):
    """Close manifest - no more orders can be added"""
    try:
        manifest_uuid = UUID(manifest_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid manifest ID")
    
    manifest = db.query(Manifest).filter(Manifest.id == manifest_uuid).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    if manifest.status != ManifestStatus.OPEN:
        raise HTTPException(status_code=400, detail="Manifest already closed")
    
    manifest.status = ManifestStatus.CLOSED
    manifest.closed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "manifest_number": manifest.manifest_number,
        "status": manifest.status.value,
        "message": f"Manifest {manifest.manifest_number} closed"
    }


@manifest_router.post("/{manifest_id}/pickup")
def mark_manifest_picked_up(
    manifest_id: str,
    db: Session = Depends(get_db)
):
    """Mark manifest as picked up by courier"""
    try:
        manifest_uuid = UUID(manifest_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid manifest ID")
    
    manifest = db.query(Manifest).filter(Manifest.id == manifest_uuid).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    manifest.status = ManifestStatus.PICKED_UP
    manifest.picked_up_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "manifest_number": manifest.manifest_number,
        "status": manifest.status.value,
        "message": f"Manifest {manifest.manifest_number} marked as picked up"
    }


@manifest_router.delete("/{manifest_id}")
def delete_manifest(
    manifest_id: str,
    db: Session = Depends(get_db)
):
    """Delete manifest (only if open and empty)"""
    try:
        manifest_uuid = UUID(manifest_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid manifest ID")
    
    manifest = db.query(Manifest).filter(Manifest.id == manifest_uuid).first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    if manifest.status != ManifestStatus.OPEN:
        raise HTTPException(status_code=400, detail="Can only delete open manifests")
    
    if manifest.order_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete manifest with orders")
    
    db.delete(manifest)
    db.commit()
    
    return {
        "success": True,
        "message": "Manifest deleted"
    }
