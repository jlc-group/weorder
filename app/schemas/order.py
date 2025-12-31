"""
Order Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class OrderItemCreate(BaseModel):
    product_id: Optional[UUID] = None
    sku: str
    product_name: Optional[str] = None
    quantity: int = 1
    unit_price: Decimal = Decimal("0")
    line_discount: Decimal = Decimal("0")
    line_type: str = "NORMAL"

class OrderCreate(BaseModel):
    external_order_id: Optional[str] = None
    channel_code: str = "manual"
    company_id: UUID
    warehouse_id: Optional[UUID] = None
    
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    
    payment_method: Optional[str] = None
    shipping_method: Optional[str] = None
    
    shipping_fee: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    
    items: List[OrderItemCreate] = []

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_fee: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    status_normalized: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: UUID
    sku: str
    product_name: Optional[str]
    quantity: int
    unit_price: Decimal
    line_discount: Decimal
    line_total: Decimal
    line_type: str

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: UUID
    external_order_id: Optional[str]
    channel_code: str
    status_normalized: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    total_amount: Decimal
    order_datetime: Optional[datetime]
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
