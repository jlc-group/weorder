"""
Product & SKU Models
"""
from sqlalchemy import Column, String, Numeric, Boolean, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class Product(Base, UUIDMixin, TimestampMixin):
    """Product Master"""
    __tablename__ = "product"
    
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text)
    product_type = Column(String(20), default="NORMAL")  # NORMAL, SET, GIFT
    standard_cost = Column(Numeric(12, 2), default=0)
    standard_price = Column(Numeric(12, 2), default=0)
    currency_code = Column(String(3), default="THB")
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    reorder_point = Column(Integer, default=10)  # Low stock alert threshold
    target_days_to_keep = Column(Integer, default=30)  # Smart Reorder: Target days of inventory
    lead_time_days = Column(Integer, default=7)  # Smart Reorder: Estimated lead time
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    stock_ledger = relationship("StockLedger", back_populates="product")
    stock_balances = relationship("StockBalance", back_populates="product")
    # BOM relationships
    set_components = relationship("ProductSetBom", foreign_keys="ProductSetBom.set_product_id", back_populates="set_product")
    component_of = relationship("ProductSetBom", foreign_keys="ProductSetBom.component_product_id", back_populates="component_product")

class ProductSetBom(Base, UUIDMixin):
    """Product Set Bill of Materials"""
    __tablename__ = "product_set_bom"
    
    set_product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False)
    component_product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    
    # Relationships
    set_product = relationship("Product", foreign_keys=[set_product_id], back_populates="set_components")
    component_product = relationship("Product", foreign_keys=[component_product_id], back_populates="component_of")
