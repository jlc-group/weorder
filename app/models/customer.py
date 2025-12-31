"""
Customer Models
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class CustomerAccount(Base, UUIDMixin, TimestampMixin):
    """Customer Account"""
    __tablename__ = "customer_account"
    
    external_ref = Column(String(100))  # Reference to external CRM
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), index=True)
    email = Column(String(200))
    line_id = Column(String(100))
    address = Column(Text)
    notes = Column(Text)
    
    # Relationships
    orders = relationship("OrderHeader", back_populates="customer")
    invoice_profiles = relationship("InvoiceProfile", back_populates="customer")
    loyalty_links = relationship("LoyaltyLink", back_populates="customer")
