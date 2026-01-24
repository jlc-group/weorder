"""
Order Models
"""
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class OrderHeader(Base, UUIDMixin, TimestampMixin):
    """Order Header"""
    __tablename__ = "order_header"
    
    # External reference
    external_order_id = Column(String(100), index=True)
    channel_code = Column(String(50), ForeignKey("sales_channel.code"), nullable=False)
    
    # Company & Warehouse
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouse.id"))
    
    # Customer
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customer_account.id"))
    customer_name = Column(String(200))
    customer_phone = Column(String(20))
    customer_address = Column(Text)
    
    # Status
    status_raw = Column(String(50))  # Original platform status
    status_normalized = Column(String(20), default="NEW", index=True)  # NEW, PAID, PACKING, SHIPPED, DELIVERED, CANCELLED, RETURNED
    
    # Payment
    payment_method = Column(String(50))  # COD, TRANSFER, CREDIT_CARD, etc.
    payment_status = Column(String(20), default="PENDING")  # PENDING, PARTIAL, PAID
    
    # Shipping
    shipping_method = Column(String(50))
    courier_code = Column(String(50))
    tracking_number = Column(String(100))
    
    # Campaign
    campaign_code = Column(String(100))
    live_tag = Column(String(100))

    # Order Source Classification
    is_affiliate_order = Column(Boolean, default=False)  # Order from affiliate/creator
    is_live_order = Column(Boolean, default=False)  # Order from live stream

    # Dates
    order_datetime = Column(DateTime(timezone=True))
    shipped_at = Column(DateTime(timezone=True))
    rts_time = Column(DateTime(timezone=True))  # Ready To Ship time
    paid_time = Column(DateTime(timezone=True))
    delivery_time = Column(DateTime(timezone=True))
    collection_time = Column(DateTime(timezone=True))
    
    # Return Tracking
    returned_at = Column(DateTime(timezone=True))  # When items were returned to warehouse
    return_reason = Column(String(50))  # DELIVERY_FAILED, CUSTOMER_RETURN, DAMAGED, WRONG_ITEM
    return_verified = Column(Boolean, default=False)  # Has the return been verified?
    return_verified_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))  # Who verified
    return_notes = Column(Text)  # Notes about the return (condition, missing items, etc.)
    
    # Shipping Fee Details
    original_shipping_fee = Column(Numeric(12, 2), default=0)
    shipping_fee_platform_discount = Column(Numeric(12, 2), default=0)
    is_cod = Column(Boolean, default=False)
    
    # Currency
    currency_code = Column(String(3), default="THB")
    
    # Amounts
    subtotal_amount = Column(Numeric(12, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)  # Shop discount
    platform_discount_amount = Column(Numeric(12, 2), default=0)  # Platform discount
    shipping_fee = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    
    # Order-level discount info
    order_discount_type = Column(String(20))  # PERCENT, AMOUNT, NONE
    order_discount_rate = Column(Numeric(5, 4))  # e.g., 0.30 = 30%
    order_discount_code = Column(String(50))
    order_discount_label = Column(String(200))
    
    # Pre-pack box assignment
    box_uid = Column(String(50), ForeignKey("prepack_box.box_uid"))
    
    # User references
    sales_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    
    # Raw data from platform
    raw_payload = Column(JSONB)
    
    # Relationships
    company = relationship("Company", back_populates="orders")
    warehouse = relationship("Warehouse", back_populates="orders")
    customer = relationship("CustomerAccount", back_populates="orders")
    channel = relationship("SalesChannel", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    memos = relationship("OrderMemo", back_populates="order", cascade="all, delete-orphan")
    prepack_box = relationship("PrepackBox", foreign_keys=[box_uid], back_populates="assigned_order")
    creator = relationship("AppUser", foreign_keys=[created_by], back_populates="orders_created")
    sales_person = relationship("AppUser", foreign_keys=[sales_by], back_populates="orders_sold")
    payments = relationship("PaymentAllocation", back_populates="order")
    profit = relationship("OrderProfit", back_populates="order", uselist=False)
    
    # Unique constraint for channel + external_order_id
    __table_args__ = (
        Index("ix_order_channel_external", channel_code, external_order_id, unique=True),
    )

class OrderItem(Base, UUIDMixin):
    """Order Item/Line"""
    __tablename__ = "order_item"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"))
    
    sku = Column(String(100), nullable=False)
    product_name = Column(String(300))
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), default=0)
    
    # Line discount
    line_discount = Column(Numeric(12, 2), default=0)
    discount_type = Column(String(20))  # PERCENT, AMOUNT, NONE
    discount_rate = Column(Numeric(5, 4))
    discount_source = Column(String(20))  # SHOP, PLATFORM, PROMOTION, MANUAL
    discount_code = Column(String(50))
    discount_label = Column(String(200))
    
    # Line total (after discount)
    line_total = Column(Numeric(12, 2), default=0)
    
    # Original price and discount breakdown
    original_price = Column(Numeric(12, 2), default=0)
    platform_discount = Column(Numeric(12, 2), default=0)
    seller_discount = Column(Numeric(12, 2), default=0)
    
    # Line type
    line_type = Column(String(20), default="NORMAL")  # NORMAL, FREE_GIFT, BUNDLE_COMPONENT, FREE_PROMO
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotion.id"))
    
    # Relationships
    order = relationship("OrderHeader", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    promotion = relationship("Promotion")

class OrderMemo(Base, UUIDMixin, TimestampMixin):
    """Order Memo/Notes"""
    __tablename__ = "order_memo"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    memo_type = Column(String(20), default="NOTE")  # NOTE, SYSTEM, PROMOTION, CS
    content = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    
    # Relationships
    order = relationship("OrderHeader", back_populates="memos")
