"""
Stock & Inventory Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
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

class Location(Base, UUIDMixin):
    """Warehouse Location (Zone/Shelf/Bin)"""
    __tablename__ = "location"
    
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # e.g., "A-01-01"
    location_type = Column(String(20), default="BIN")  # ZONE, RACK, SHELF, BIN
    description = Column(Text)
    is_active = Column(Integer, default=1)  # Using Integer for compatibility or Boolean? Base uses Boolean usually. Using Integer as per older patterns or Boolean? 
    # Let's check other models. Warehouse uses Boolean. Product uses Boolean.
    # Let's use Boolean.
    # Wait, check if I need to import anything. Boolean is imported.
    is_active = Column(Boolean, default=True)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="locations")
    stock_balances = relationship("StockBalance", back_populates="location")

class StockBalance(Base, UUIDMixin):
    """Current Stock Balance Snapshot"""
    __tablename__ = "stock_balance"
    
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("location.id"), nullable=True, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False, index=True)
    
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="stock_balances")
    location = relationship("Location", back_populates="stock_balances")
    product = relationship("Product", back_populates="stock_balances")
