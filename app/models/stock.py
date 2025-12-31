"""
Stock & Inventory Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core import Base
from .base import UUIDMixin

class StockLedger(Base, UUIDMixin):
    """Stock Movement Ledger"""
    __tablename__ = "stock_ledger"
    
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False, index=True)
    box_uid = Column(String(50))  # For pre-pack related movements
    
    # Movement info
    movement_type = Column(String(20), nullable=False)  # IN, OUT, RESERVE, RELEASE, ADJUST
    quantity = Column(Integer, nullable=False)  # Positive or negative
    
    # Reference
    reference_type = Column(String(30))  # ORDER, PREPACK_JOB, ADJUSTMENT, INITIAL
    reference_id = Column(String(50))  # ID of related record
    
    # Metadata
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="stock_ledger")
    product = relationship("Product", back_populates="stock_ledger")
