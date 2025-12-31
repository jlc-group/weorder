"""
Product Schemas
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from decimal import Decimal

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    product_type: str = "NORMAL"
    standard_cost: Decimal = Decimal("0")
    standard_price: Decimal = Decimal("0")
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    product_type: Optional[str] = None
    standard_cost: Optional[Decimal] = None
    standard_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    description: Optional[str]
    product_type: str
    standard_cost: Decimal
    standard_price: Decimal
    image_url: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True
