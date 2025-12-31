"""
Integration Models - Platform configuration, sync jobs, webhook logs
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class PlatformType(str, enum.Enum):
    SHOPEE = "shopee"
    LAZADA = "lazada"
    TIKTOK = "tiktok"


class SyncJobType(str, enum.Enum):
    POLL = "POLL"
    WEBHOOK = "WEBHOOK"


class SyncJobStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PlatformConfig(Base):
    """
    Platform API configuration and credentials per shop
    """
    __tablename__ = "platform_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(30), nullable=False)  # shopee, lazada, tiktok
    shop_id = Column(String(100), nullable=False)
    shop_name = Column(String(200))
    
    # API Credentials (should be encrypted in production)
    app_key = Column(String(200))
    app_secret = Column(String(500))  # encrypted
    access_token = Column(Text)  # encrypted
    refresh_token = Column(Text)  # encrypted
    token_expires_at = Column(DateTime)
    
    # Webhook configuration
    webhook_secret = Column(String(200))
    webhook_url = Column(String(500))
    
    # Settings
    is_active = Column(Boolean, default=True)
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=15)
    last_sync_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sync_jobs = relationship("SyncJob", back_populates="platform_config", cascade="all, delete-orphan")

    __table_args__ = (
        # Unique constraint: one shop per platform
        {"schema": None},
    )

    def __repr__(self):
        return f"<PlatformConfig {self.platform}:{self.shop_id}>"


class SyncJob(Base):
    """
    Track sync job history and status
    """
    __tablename__ = "sync_job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_config_id = Column(UUID(as_uuid=True), ForeignKey("platform_config.id"), nullable=False)
    
    job_type = Column(String(20), default="POLL")  # POLL, WEBHOOK
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(20), default="RUNNING")  # RUNNING, SUCCESS, FAILED
    
    # Stats
    orders_fetched = Column(Integer, default=0)
    orders_created = Column(Integer, default=0)
    orders_updated = Column(Integer, default=0)
    orders_skipped = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSONB)
    
    # Relationships
    platform_config = relationship("PlatformConfig", back_populates="sync_jobs")

    def __repr__(self):
        return f"<SyncJob {self.id} {self.job_type} {self.status}>"
    
    def mark_success(self):
        self.status = "SUCCESS"
        self.finished_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str, error_details: dict = None):
        self.status = "FAILED"
        self.finished_at = datetime.utcnow()
        self.error_message = error_message
        self.error_details = error_details


class WebhookLog(Base):
    """
    Log incoming webhook payloads for debugging and replay
    """
    __tablename__ = "webhook_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(30), nullable=False)  # shopee, lazada, tiktok
    event_type = Column(String(50))  # order.created, order.status.changed, etc.
    
    # Request data
    payload = Column(JSONB)
    headers = Column(JSONB)
    signature = Column(String(500))
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    process_result = Column(String(50))  # SUCCESS, FAILED, SKIPPED
    process_error = Column(Text)
    
    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50))

    def __repr__(self):
        return f"<WebhookLog {self.platform} {self.event_type} {self.received_at}>"
    
    def mark_processed(self, result: str, error: str = None):
        self.processed = True
        self.processed_at = datetime.utcnow()
        self.process_result = result
        self.process_error = error
