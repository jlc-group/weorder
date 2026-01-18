"""
Label Print Log Model
Tracks when shipping labels are printed for orders
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class LabelPrintLog(Base):
    """Log for tracking printed shipping labels"""
    __tablename__ = "label_print_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Order reference (no FK for simpler creation)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    external_order_id = Column(String(100), index=True)
    
    # Platform info
    platform = Column(String(20), nullable=False)  # shopee, tiktok, lazada
    
    # Print details
    printed_at = Column(DateTime, nullable=False, default=datetime.now)
    printed_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Batch tracking (for bulk prints)
    batch_id = Column(String(50), nullable=True, index=True)
    batch_date = Column(DateTime, nullable=True)  # Date this batch belongs to
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_label_print_platform_date', 'platform', 'printed_at'),
        Index('ix_label_print_batch', 'batch_id', 'batch_date'),
    )

    def __repr__(self):
        return f"<LabelPrintLog {self.external_order_id} @ {self.printed_at}>"
