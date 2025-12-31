"""
Pre-pack & Packing Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core import Base
from .base import UUIDMixin

class PrepackBox(Base):
    """Pre-pack Box"""
    __tablename__ = "prepack_box"
    
    box_uid = Column(String(50), primary_key=True)  # e.g., PK20251231-00001
    set_product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"))
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouse.id"), nullable=False)
    
    # Status
    status = Column(String(30), default="PREPACK_READY")  # PREPACK_READY, ASSIGNED_TO_ORDER, REOPEN_FOR_PROMO, SHIPPED, RETURNED, USED
    current_version = Column(Integer, default=1)
    
    # Order assignment
    order_id = Column(UUID(as_uuid=True))  # Not FK to avoid circular reference
    
    # Packing info
    first_packed_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    first_packed_at = Column(DateTime(timezone=True))
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    last_modified_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="prepack_boxes")
    items = relationship("PrepackBoxItem", back_populates="box", cascade="all, delete-orphan")
    sessions = relationship("PackingSession", back_populates="box", cascade="all, delete-orphan")
    assigned_order = relationship("OrderHeader", foreign_keys="OrderHeader.box_uid", back_populates="prepack_box")

class PrepackBoxItem(Base, UUIDMixin):
    """Items inside a pre-pack box (versioned)"""
    __tablename__ = "prepack_box_item"
    
    box_uid = Column(String(50), ForeignKey("prepack_box.box_uid"), nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False)
    sku = Column(String(100), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    
    line_type = Column(String(20), default="NORMAL")  # NORMAL, FREE_PROMO, EXTRA
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotion.id"))
    
    # Relationships
    box = relationship("PrepackBox", back_populates="items")
    product = relationship("Product")

class PackingSession(Base, UUIDMixin):
    """Packing Video Session"""
    __tablename__ = "packing_session"
    
    box_uid = Column(String(50), ForeignKey("prepack_box.box_uid"), nullable=False)
    version_no = Column(Integer, default=1, nullable=False)
    
    action_type = Column(String(30), default="PREPACK_INITIAL")  # PREPACK_INITIAL, REPACK_FOR_PROMO, REPACK_FOR_QC
    video_path = Column(String(500))
    
    packed_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    packed_at = Column(DateTime(timezone=True), server_default=func.now())
    remark = Column(Text)
    
    # Relationships
    box = relationship("PrepackBox", back_populates="sessions")
