"""
Stock Schemas
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class StockMovementCreate(BaseModel):
    warehouse_id: UUID
    location_id: Optional[UUID] = None
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

# Location Schemas
class LocationBase(BaseModel):
    name: str
    location_type: str = "BIN"
    description: Optional[str] = None
    is_active: bool = True

class LocationCreate(LocationBase):
    warehouse_id: UUID

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class LocationResponse(LocationBase):
    id: UUID
    warehouse_id: UUID

    class Config:
        from_attributes = True

# Stock Balance Schema
class StockBalanceResponse(BaseModel):
    warehouse_id: UUID
    location_id: Optional[UUID]
    product_id: UUID
    quantity: int
    reserved_quantity: int
    available_quantity: int

    class Config:
        from_attributes = True
