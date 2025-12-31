"""
Order Profitability Model
"""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core import Base

class OrderProfit(Base):
    """Order Profit/Loss Calculation"""
    __tablename__ = "order_profit"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"))
    
    # Revenue
    total_revenue = Column(Numeric(12, 2), default=0)
    
    # Costs
    cogs_total = Column(Numeric(12, 2), default=0)  # Cost of goods sold
    platform_fee_total = Column(Numeric(12, 2), default=0)
    fulfillment_cost_total = Column(Numeric(12, 2), default=0)  # Box, packing, shipping
    promo_cost_total = Column(Numeric(12, 2), default=0)  # Free gifts cost
    refund_total = Column(Numeric(12, 2), default=0)
    
    # Profit
    gross_profit = Column(Numeric(12, 2), default=0)
    net_profit = Column(Numeric(12, 2), default=0)
    profit_margin_percent = Column(Numeric(6, 2))
    
    currency_code = Column(String(3), default="THB")
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    order = relationship("OrderHeader", back_populates="profit")
