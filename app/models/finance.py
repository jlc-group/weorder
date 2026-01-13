"""
Finance & Payment Models
"""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class PaymentReceipt(Base, UUIDMixin, TimestampMixin):
    """Payment Receipt"""
    __tablename__ = "payment_receipt"
    
    receipt_number = Column(String(50), unique=True)
    receipt_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Payment info
    payment_method = Column(String(50))  # TRANSFER, COD, CREDIT_CARD
    amount = Column(Numeric(12, 2), nullable=False)
    currency_code = Column(String(3), default="THB")
    
    # Bank info (for transfers)
    bank_account_id = Column(UUID(as_uuid=True))
    reference_number = Column(String(100))
    
    # Status
    status = Column(String(20), default="UNBOUND")  # UNBOUND, PARTIAL, FULL
    
    note = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    
    # Relationships
    allocations = relationship("PaymentAllocation", back_populates="receipt", cascade="all, delete-orphan")

class PaymentAllocation(Base, UUIDMixin):
    """Payment Allocation to Orders"""
    __tablename__ = "payment_allocation"
    
    receipt_id = Column(UUID(as_uuid=True), ForeignKey("payment_receipt.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    allocated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    receipt = relationship("PaymentReceipt", back_populates="allocations")
    order = relationship("OrderHeader", back_populates="payments")

class RefundLedger(Base, UUIDMixin, TimestampMixin):
    """Refund Ledger"""
    __tablename__ = "refund_ledger"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    
    refund_type = Column(String(20))  # FULL, PARTIAL, SHIPPING_ONLY
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Platform fee handling
    platform_fee_returned = Column(Numeric(12, 2), default=0)
    platform_fee_not_returned = Column(Numeric(12, 2), default=0)
    net_refund = Column(Numeric(12, 2))
    
    refund_date = Column(DateTime(timezone=True))
    processed_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    note = Column(Text)

class PlatformFeeLedger(Base, UUIDMixin, TimestampMixin):
    """Platform Fee Ledger"""
    __tablename__ = "platform_fee_ledger"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=False)
    
    platform_name = Column(String(50), nullable=False)  # shopee, lazada, tiktok
    fee_type = Column(String(30), nullable=False)  # COMMISSION, PAYMENT_FEE, SERVICE_FEE, ADS_FEE
    amount = Column(Numeric(12, 2), nullable=False)
    
    fee_date = Column(DateTime(timezone=True))
    payout_reference = Column(String(100))
    raw_data = Column(JSONB)

class MarketplaceTransaction(Base, UUIDMixin, TimestampMixin):
    """
    Detailed Marketplace Transaction (Money Trail)
    Stores every financial line item: Income (Item Price), Expense (Commission, Shipping, etc.)
    """
    __tablename__ = "marketplace_transaction"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_header.id"), nullable=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # shopee, tiktok, lazada
    
    # Transaction Details
    transaction_type = Column(String(100), nullable=False)  # ITEM_PRICE, COMMISSION_FEE, SHIPPING_FEE, ESCROW_RELEASE
    amount = Column(Numeric(12, 2), nullable=False)  # Positive = Income, Negative = Expense
    currency = Column(String(3), default="THB")
    
    transaction_date = Column(DateTime(timezone=True), index=True)
    status = Column(String(20), default="COMPLETED")
    
    # Context
    description = Column(Text)
    payout_reference = Column(String(100))  # Batch ID / Escrow ID
    raw_data = Column(JSONB)  # Full payload from API
