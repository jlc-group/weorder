"""
Tax Invoice Profile Model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class InvoiceProfile(Base, UUIDMixin, TimestampMixin):
    """Tax Invoice Profile (Customer Portal)"""
    __tablename__ = "invoice_profile"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customer_account.id"))
    
    # Profile type
    profile_type = Column(String(20), default="PERSONAL")  # PERSONAL, COMPANY
    
    # Tax info
    tax_id = Column(String(20))
    branch = Column(String(50))  # HQ or branch number (e.g., "00000" for HQ)
    
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
    
    # Status: PENDING → ISSUED or REJECTED
    status = Column(String(30), default="PENDING")  # PENDING, ISSUED, REJECTED
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime(timezone=True))
    
    # PDF Storage (path to generated PDF file)
    invoice_pdf_path = Column(String(500))
    
    # Issued tracking
    issued_at = Column(DateTime(timezone=True))
    
    # Rejection tracking
    rejected_reason = Column(Text)
    rejected_at = Column(DateTime(timezone=True))
    
    # Source
    created_source = Column(String(20), default="CUSTOMER_PORTAL")  # CUSTOMER_PORTAL, INTERNAL, PLATFORM_SYNC
    
    # Platform Data (raw data from Platform API)
    platform_invoice_data = Column(JSONB)  # Raw invoice_data from Shopee/Lazada API
    platform_synced_at = Column(DateTime(timezone=True))  # When data was synced from platform
    
    # Staff notes
    notes = Column(Text)
    
    # Relationships
    customer = relationship("CustomerAccount", back_populates="invoice_profiles")
    order = relationship("OrderHeader", backref="invoice_profile", uselist=False)

