"""
Packing Batch Model - For managing packing waves/batches
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class PackingBatch(Base):
    """
    A batch/wave of orders to be packed.
    Created when user clicks "สร้างรอบแพ็ค" to cut off orders at a specific time.
    """
    __tablename__ = "packing_batch"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Batch info
    batch_number = Column(Integer, nullable=False)  # Sequential number for the day
    batch_date = Column(DateTime, nullable=False)   # Date of the batch (date only)
    
    # Sync info
    synced_at = Column(DateTime)        # When orders were synced from marketplace
    cutoff_at = Column(DateTime)        # When batch was created (cutoff time)
    
    # Stats
    order_count = Column(Integer, default=0)        # Total orders in batch
    packed_count = Column(Integer, default=0)       # Orders already packed
    printed_count = Column(Integer, default=0)      # Labels printed
    
    # Status: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    status = Column(String(20), default="PENDING")
    
    # Platform filter (optional - NULL means all platforms)
    platform = Column(String(30))  # tiktok, shopee, lazada, or NULL for all
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("PackingBatchOrder", back_populates="batch", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PackingBatch {self.batch_date.date()} #{self.batch_number} - {self.order_count} orders>"


class PackingBatchOrder(Base):
    """
    Junction table linking orders to batches.
    An order can only belong to one batch.
    """
    __tablename__ = "packing_batch_order"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    batch_id = Column(UUID(as_uuid=True), ForeignKey("packing_batch.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    
    # Tracking
    is_packed = Column(Boolean, default=False)
    is_printed = Column(Boolean, default=False)
    packed_at = Column(DateTime)
    printed_at = Column(DateTime)
    
    # Position in batch (for pick list ordering)
    sequence = Column(Integer)
    
    # Relationships
    batch = relationship("PackingBatch", back_populates="orders")
    order = relationship("OrderHeader")
    
    __table_args__ = (
        # Unique constraint: one order per batch
        {"schema": None},
    )
