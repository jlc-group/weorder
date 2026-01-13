"""
Sync Log Model - Track synchronization history
"""
from sqlalchemy import Column, String, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from datetime import datetime

from app.core import Base
from .base import UUIDMixin


class SyncStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SyncLog(Base, UUIDMixin):
    """Log of sync operations"""
    __tablename__ = "sync_log"
    
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(20), default=SyncStatus.RUNNING.value, nullable=False)
    
    # Platform filter (null = all platforms)
    platform = Column(String(50))
    
    # Stats JSON: {"fetched": 100, "created": 10, "updated": 5, "errors": 0}
    stats = Column(JSON, default={})
    
    # Error message if failed
    error_message = Column(String(500))
