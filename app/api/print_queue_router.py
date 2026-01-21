"""
Print Queue API - Manage orders in print queue
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

logger = logging.getLogger(__name__)

print_queue_router = APIRouter(prefix="/print-queue", tags=["print-queue"])

# In-memory print queue (per-session, could be replaced with Redis for production)
_print_queue: List[dict] = []


class PrintQueueItem(BaseModel):
    order_id: str
    external_order_id: str
    channel_code: str
    customer_name: Optional[str] = None
    added_at: datetime
    priority: int = 0


class AddToQueueRequest(BaseModel):
    order_ids: List[str]


@print_queue_router.get("")
def get_print_queue():
    """Get current print queue"""
    return {
        "queue": _print_queue,
        "count": len(_print_queue)
    }


@print_queue_router.post("/add")
def add_to_print_queue(
    request: AddToQueueRequest,
    db: Session = Depends(get_db)
):
    """Add orders to print queue"""
    added = 0
    skipped = 0
    
    # Get existing order IDs in queue
    existing_ids = {item["order_id"] for item in _print_queue}
    
    for order_id_str in request.order_ids:
        if order_id_str in existing_ids:
            skipped += 1
            continue
        
        try:
            order_uuid = UUID(order_id_str)
            order = db.query(OrderHeader).filter(OrderHeader.id == order_uuid).first()
            
            if order:
                _print_queue.append({
                    "order_id": str(order.id),
                    "external_order_id": order.external_order_id,
                    "channel_code": order.channel_code,
                    "customer_name": order.customer_name,
                    "added_at": datetime.now().isoformat(),
                    "priority": 0
                })
                existing_ids.add(order_id_str)
                added += 1
        except Exception as e:
            logger.error(f"Error adding order {order_id_str} to queue: {e}")
            continue
    
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "queue_size": len(_print_queue),
        "message": f"Added {added} orders to queue, skipped {skipped} (already in queue)"
    }


@print_queue_router.delete("/{order_id}")
def remove_from_print_queue(order_id: str):
    """Remove order from print queue"""
    global _print_queue
    
    initial_size = len(_print_queue)
    _print_queue = [item for item in _print_queue if item["order_id"] != order_id]
    
    removed = initial_size - len(_print_queue)
    
    return {
        "success": removed > 0,
        "removed": removed,
        "queue_size": len(_print_queue)
    }


@print_queue_router.delete("")
def clear_print_queue():
    """Clear entire print queue"""
    global _print_queue
    
    cleared = len(_print_queue)
    _print_queue = []
    
    return {
        "success": True,
        "cleared": cleared,
        "message": f"Cleared {cleared} items from queue"
    }


@print_queue_router.post("/reorder")
def reorder_print_queue(order_ids: List[str]):
    """Reorder print queue based on provided order"""
    global _print_queue
    
    # Create lookup
    queue_map = {item["order_id"]: item for item in _print_queue}
    
    # Reorder based on input
    new_queue = []
    for order_id in order_ids:
        if order_id in queue_map:
            new_queue.append(queue_map[order_id])
    
    # Add any remaining items not in the reorder list
    for item in _print_queue:
        if item["order_id"] not in order_ids:
            new_queue.append(item)
    
    _print_queue = new_queue
    
    return {
        "success": True,
        "queue": _print_queue,
        "count": len(_print_queue)
    }


@print_queue_router.post("/print-all")
async def print_all_from_queue(db: Session = Depends(get_db)):
    """Print all orders in queue and clear queue"""
    global _print_queue
    
    if not _print_queue:
        return {
            "success": False,
            "message": "Queue is empty"
        }
    
    order_ids = [item["order_id"] for item in _print_queue]
    
    # Clear queue after getting IDs
    count = len(_print_queue)
    _print_queue = []
    
    return {
        "success": True,
        "order_ids": order_ids,
        "count": count,
        "message": f"Ready to print {count} orders. Queue cleared."
    }
