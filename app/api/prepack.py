
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, UUID4

from app.core import get_db
from app.services.prepack_service import PrepackService

router = APIRouter(prefix="/prepack", tags=["Prepack"])

class PrepackItemRequest(BaseModel):
    product_id: UUID4
    sku: str
    quantity: int

class CreateBatchRequest(BaseModel):
    warehouse_id: UUID4
    items: List[PrepackItemRequest]
    box_count: int

@router.post("/batch/create")
def create_batch(request: CreateBatchRequest, db: Session = Depends(get_db)):
    """
    Create a batch of pre-pack boxes
    """
    try:
        items_dict = [item.dict() for item in request.items]
        boxes = PrepackService.create_batch(
            db=db,
            warehouse_id=str(request.warehouse_id),
            items=items_dict,
            quantity=request.box_count,
            created_by_id=None # Add User ID from auth later
        )
        return {"message": "Batch created successfully", "count": len(boxes), "first_uid": boxes[0].box_uid if boxes else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
def list_available_boxes(sku: str = None, db: Session = Depends(get_db)):
    """
    List available pre-pack boxes
    """
    boxes = PrepackService.get_available_boxes(db, sku)
    return {"count": len(boxes), "boxes": [{"box_uid": b.box_uid, "status": b.status} for b in boxes]}
