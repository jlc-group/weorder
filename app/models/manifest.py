"""
Manifest Model - ใบส่งสินค้ารวมสำหรับแต่ละรอบขนส่ง
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ManifestStatus(str, enum.Enum):
    OPEN = "OPEN"           # กำลังเพิ่ม orders อยู่
    CLOSED = "CLOSED"       # ปิดแล้ว พร้อมส่ง
    PICKED_UP = "PICKED_UP" # ขนส่งรับแล้ว


class Manifest(Base):
    __tablename__ = "manifest"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_number = Column(String(50), unique=True, nullable=False)  # MNFT-2026-01-21-001
    
    # Details
    platform = Column(String(30))  # tiktok, shopee, lazada หรือ mixed
    courier = Column(String(50))   # Flash, Kerry, J&T etc.
    status = Column(SQLEnum(ManifestStatus), default=ManifestStatus.OPEN)
    
    # Counts
    order_count = Column(Integer, default=0)
    parcel_count = Column(Integer, default=0)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    picked_up_at = Column(DateTime)
    
    # Who handled
    created_by = Column(String(100))
    closed_by = Column(String(100))
    
    # Relationships
    items = relationship("ManifestItem", back_populates="manifest", cascade="all, delete-orphan")
    
    def generate_manifest_number(self):
        """Generate manifest number like MNFT-2026-01-21-001"""
        date_part = datetime.now().strftime("%Y-%m-%d")
        return f"MNFT-{date_part}-{uuid.uuid4().hex[:6].upper()}"


class ManifestItem(Base):
    __tablename__ = "manifest_item"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_id = Column(UUID(as_uuid=True), ForeignKey("manifest.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    
    # Denormalized for quick access
    external_order_id = Column(String(100))
    tracking_number = Column(String(100))
    customer_name = Column(String(200))
    
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    manifest = relationship("Manifest", back_populates="items")
    order = relationship("OrderHeader")
