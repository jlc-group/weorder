"""
Loyalty & Saversure Integration Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core import Base
from .base import UUIDMixin

class LoyaltyLink(Base, UUIDMixin):
    """Link between WeOrder customer and Saversure member"""
    __tablename__ = "loyalty_link"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customer_account.id"), nullable=False)
    saversure_member_id = Column(String(50), nullable=False)
    
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    customer = relationship("CustomerAccount", back_populates="loyalty_links")

class LoyaltyEarnTx(Base, UUIDMixin):
    """Loyalty Points Earning Transaction"""
    __tablename__ = "loyalty_earn_tx"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customer_account.id"))
    saversure_member_id = Column(String(50))
    channel_code = Column(String(50))
    
    # Points
    points_earned = Column(Integer, default=0)
    
    # Status
    earn_status = Column(String(20), default="PENDING")  # PENDING, SENT, CONFIRMED, FAILED, REVERSED
    earn_date = Column(DateTime(timezone=True))
    
    # API response
    raw_response = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
