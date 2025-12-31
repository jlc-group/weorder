"""
Tax Invoice Profile Model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class InvoiceProfile(Base, UUIDMixin, TimestampMixin):
    """Tax Invoice Profile (Customer Portal)"""
    __tablename__ = "invoice_profile"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customer_account.id"))
    
    # Profile type
    profile_type = Column(String(20), default="PERSONAL")  # PERSONAL, COMPANY
    
    # Tax info
    tax_id = Column(String(20))
    branch = Column(String(50))  # HQ or branch number
    
    # Invoice details
    invoice_name = Column(String(200), nullable=False)
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    subdistrict = Column(String(100))
    district = Column(String(100))
    province = Column(String(100))
    postal_code = Column(String(10))
    phone = Column(String(20))
    email = Column(String(200))
    
    # Status
    status = Column(String(30), default="PENDING")  # PENDING, READY_FOR_INVOICE, INVOICE_ISSUED, LOCKED
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime(timezone=True))
    
    # Source
    created_source = Column(String(20), default="INTERNAL")  # CUSTOMER_PORTAL, INTERNAL
    locked_at = Column(DateTime(timezone=True))
    
    # Relationships
    customer = relationship("CustomerAccount", back_populates="invoice_profiles")
