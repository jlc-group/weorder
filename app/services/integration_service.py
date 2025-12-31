"""
Integration Service - Manage platform configurations
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.integration import PlatformConfig, SyncJob, WebhookLog
from app.integrations import ShopeeClient, LazadaClient, TikTokClient, BasePlatformClient

logger = logging.getLogger(__name__)


def get_platform_configs(
    db: Session,
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[PlatformConfig]:
    """Get all platform configurations with optional filters"""
    query = db.query(PlatformConfig)
    
    if platform:
        query = query.filter(PlatformConfig.platform == platform)
    if is_active is not None:
        query = query.filter(PlatformConfig.is_active == is_active)
    
    return query.order_by(PlatformConfig.created_at.desc()).all()


def get_platform_config(db: Session, config_id: str) -> Optional[PlatformConfig]:
    """Get platform configuration by ID"""
    return db.query(PlatformConfig).filter(PlatformConfig.id == config_id).first()


def get_platform_config_by_shop(
    db: Session,
    platform: str,
    shop_id: str,
) -> Optional[PlatformConfig]:
    """Get platform configuration by platform and shop_id"""
    return db.query(PlatformConfig).filter(
        and_(
            PlatformConfig.platform == platform,
            PlatformConfig.shop_id == shop_id,
        )
    ).first()


def create_platform_config(
    db: Session,
    platform: str,
    shop_id: str,
    shop_name: str,
    app_key: str,
    app_secret: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_expires_at: Optional[datetime] = None,
    sync_interval_minutes: int = 15,
) -> PlatformConfig:
    """Create new platform configuration"""
    config = PlatformConfig(
        platform=platform,
        shop_id=shop_id,
        shop_name=shop_name,
        app_key=app_key,
        app_secret=app_secret,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
        sync_interval_minutes=sync_interval_minutes,
        is_active=True,
        sync_enabled=True,
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"Created platform config: {platform} - {shop_name}")
    return config


def update_platform_config(
    db: Session,
    config_id: str,
    **kwargs,
) -> Optional[PlatformConfig]:
    """Update platform configuration"""
    config = get_platform_config(db, config_id)
    if not config:
        return None
    
    allowed_fields = [
        "shop_name", "app_key", "app_secret", "access_token", "refresh_token",
        "token_expires_at", "webhook_secret", "webhook_url", "is_active",
        "sync_enabled", "sync_interval_minutes",
    ]
    
    for field, value in kwargs.items():
        if field in allowed_fields and value is not None:
            setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    logger.info(f"Updated platform config: {config.platform} - {config.shop_name}")
    return config


def update_tokens(
    db: Session,
    config_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: datetime,
) -> Optional[PlatformConfig]:
    """Update OAuth tokens for platform config"""
    config = get_platform_config(db, config_id)
    if not config:
        return None
    
    config.access_token = access_token
    config.refresh_token = refresh_token
    config.token_expires_at = expires_at
    config.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(config)
    
    logger.info(f"Updated tokens for: {config.platform} - {config.shop_name}")
    return config


def delete_platform_config(db: Session, config_id: str) -> bool:
    """Delete platform configuration"""
    config = get_platform_config(db, config_id)
    if not config:
        return False
    
    db.delete(config)
    db.commit()
    
    logger.info(f"Deleted platform config: {config.platform} - {config.shop_name}")
    return True


def get_client_for_config(config: PlatformConfig) -> BasePlatformClient:
    """Create appropriate platform client from config"""
    clients = {
        "shopee": ShopeeClient,
        "lazada": LazadaClient,
        "tiktok": TikTokClient,
    }
    
    client_class = clients.get(config.platform)
    if not client_class:
        raise ValueError(f"Unknown platform: {config.platform}")
    
    return client_class(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token,
    )


# ========== Sync Jobs ==========

def create_sync_job(
    db: Session,
    platform_config_id: str,
    job_type: str = "POLL",
) -> SyncJob:
    """Create new sync job record"""
    job = SyncJob(
        platform_config_id=platform_config_id,
        job_type=job_type,
        status="RUNNING",
        started_at=datetime.utcnow(),
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return job


def complete_sync_job(
    db: Session,
    job_id: str,
    orders_fetched: int = 0,
    orders_created: int = 0,
    orders_updated: int = 0,
    orders_skipped: int = 0,
    error_message: Optional[str] = None,
) -> SyncJob:
    """Mark sync job as completed"""
    job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
    if not job:
        return None
    
    job.finished_at = datetime.utcnow()
    job.orders_fetched = orders_fetched
    job.orders_created = orders_created
    job.orders_updated = orders_updated
    job.orders_skipped = orders_skipped
    
    if error_message:
        job.status = "FAILED"
        job.error_message = error_message
    else:
        job.status = "SUCCESS"
    
    db.commit()
    db.refresh(job)
    
    return job


def get_sync_jobs(
    db: Session,
    platform_config_id: Optional[str] = None,
    limit: int = 50,
) -> List[SyncJob]:
    """Get sync job history"""
    query = db.query(SyncJob)
    
    if platform_config_id:
        query = query.filter(SyncJob.platform_config_id == platform_config_id)
    
    return query.order_by(SyncJob.started_at.desc()).limit(limit).all()


# ========== Webhook Logs ==========

def log_webhook(
    db: Session,
    platform: str,
    event_type: str,
    payload: dict,
    headers: dict = None,
    signature: str = None,
    ip_address: str = None,
) -> WebhookLog:
    """Log incoming webhook"""
    log = WebhookLog(
        platform=platform,
        event_type=event_type,
        payload=payload,
        headers=headers,
        signature=signature,
        ip_address=ip_address,
        processed=False,
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def mark_webhook_processed(
    db: Session,
    log_id: str,
    result: str,
    error: str = None,
) -> WebhookLog:
    """Mark webhook as processed"""
    log = db.query(WebhookLog).filter(WebhookLog.id == log_id).first()
    if not log:
        return None
    
    log.mark_processed(result, error)
    db.commit()
    db.refresh(log)
    
    return log


def get_unprocessed_webhooks(
    db: Session,
    platform: Optional[str] = None,
    limit: int = 100,
) -> List[WebhookLog]:
    """Get unprocessed webhooks for retry"""
    query = db.query(WebhookLog).filter(WebhookLog.processed == False)
    
    if platform:
        query = query.filter(WebhookLog.platform == platform)
    
    return query.order_by(WebhookLog.received_at.asc()).limit(limit).all()
