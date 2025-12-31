"""
Promotion Models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class Promotion(Base, UUIDMixin, TimestampMixin):
    """Promotion Master"""
    __tablename__ = "promotion"
    
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Channel filter
    channel_filter = Column(String(50))  # shopee, tiktok_live, all, etc.
    campaign_code = Column(String(100))
    live_tag = Column(String(100))
    
    # Duration
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))
    
    # Condition
    condition_type = Column(String(30))  # MIN_ORDER_AMOUNT, MIN_QTY, SKU_CONTAINS
    condition_json = Column(JSONB)  # Detailed condition parameters
    
    # Limits
    max_free_per_order = Column(Integer)
    max_free_per_cust = Column(Integer)
    
    # Priority & Status
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    actions = relationship("PromotionAction", back_populates="promotion", cascade="all, delete-orphan")

class PromotionAction(Base, UUIDMixin):
    """Promotion Action (what happens when promotion triggers)"""
    __tablename__ = "promotion_action"
    
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotion.id"), nullable=False)
    
    action_type = Column(String(30), default="ADD_FREE_ITEM")  # ADD_FREE_ITEM, DISCOUNT_PERCENT, etc.
    
    # Free item details
    free_product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"))
    free_sku = Column(String(100))
    free_quantity = Column(Integer, default=1)
    
    # Relationships
    promotion = relationship("Promotion", back_populates="actions")
    product = relationship("Product")
