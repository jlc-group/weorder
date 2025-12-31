"""
Audit Log Model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core import Base
from .base import UUIDMixin

class AuditLog(Base, UUIDMixin):
    """Audit Log for tracking changes"""
    __tablename__ = "audit_log"
    
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(String(50), nullable=False, index=True)
    
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE, LOGIN, STATUS_CHANGE
    
    performed_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"))
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Before/After data
    before_data = Column(JSONB)
    after_data = Column(JSONB)
    
    # Additional context
    ip_address = Column(String(50))
    user_agent = Column(String(500))
