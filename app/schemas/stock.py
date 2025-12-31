"""
Stock Schemas
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class StockMovementCreate(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    movement_type: str  # IN, OUT, RESERVE, RELEASE, ADJUST
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    note: Optional[str] = None

class StockSummary(BaseModel):
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_name: str
    on_hand: int
    reserved: int
    available: int

    class Config:
        from_attributes = True
