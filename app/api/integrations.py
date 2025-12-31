"""
Integrations API - CRUD for platform configurations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from app.core.database import get_db
from app.services import integration_service, sync_service

logger = logging.getLogger(__name__)

integrations_router = APIRouter(prefix="/integrations", tags=["integrations"])


# ========== Schemas ==========

class PlatformConfigCreate(BaseModel):
    platform: str  # shopee, lazada, tiktok
    shop_id: str
    shop_name: str
    app_key: str
    app_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    sync_interval_minutes: int = 15


class PlatformConfigUpdate(BaseModel):
    shop_name: Optional[str] = None
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    is_active: Optional[bool] = None
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None


class PlatformConfigResponse(BaseModel):
    id: str
    platform: str
    shop_id: str
    shop_name: Optional[str]
    is_active: bool
    sync_enabled: bool
    sync_interval_minutes: int
    last_sync_at: Optional[datetime]
    token_expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SyncJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    orders_fetched: int
    orders_created: int
    orders_updated: int
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class SyncTriggerRequest(BaseModel):
    hours_back: int = 24


# ========== Platform Config Endpoints ==========

@integrations_router.get("/platforms", response_model=List[PlatformConfigResponse])
async def list_platform_configs(
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List all platform configurations"""
    configs = integration_service.get_platform_configs(db, platform, is_active)
    return [
        PlatformConfigResponse(
            id=str(c.id),
            platform=c.platform,
            shop_id=c.shop_id,
            shop_name=c.shop_name,
            is_active=c.is_active,
            sync_enabled=c.sync_enabled,
            sync_interval_minutes=c.sync_interval_minutes,
            last_sync_at=c.last_sync_at,
            token_expires_at=c.token_expires_at,
            created_at=c.created_at,
        )
        for c in configs
    ]


@integrations_router.get("/platforms/{config_id}", response_model=PlatformConfigResponse)
async def get_platform_config(
    config_id: str,
    db: Session = Depends(get_db),
):
    """Get platform configuration by ID"""
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    return PlatformConfigResponse(
        id=str(config.id),
        platform=config.platform,
        shop_id=config.shop_id,
        shop_name=config.shop_name,
        is_active=config.is_active,
        sync_enabled=config.sync_enabled,
        sync_interval_minutes=config.sync_interval_minutes,
        last_sync_at=config.last_sync_at,
        token_expires_at=config.token_expires_at,
        created_at=config.created_at,
    )


@integrations_router.post("/platforms", response_model=PlatformConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_config(
    data: PlatformConfigCreate,
    db: Session = Depends(get_db),
):
    """Create new platform configuration"""
    # Check if already exists
    existing = integration_service.get_platform_config_by_shop(db, data.platform, data.shop_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Platform config already exists for {data.platform}/{data.shop_id}"
        )
    
    # Validate platform
    if data.platform not in ["shopee", "lazada", "tiktok"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Must be: shopee, lazada, tiktok")
    
    config = integration_service.create_platform_config(
        db=db,
        platform=data.platform,
        shop_id=data.shop_id,
        shop_name=data.shop_name,
        app_key=data.app_key,
        app_secret=data.app_secret,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        sync_interval_minutes=data.sync_interval_minutes,
    )
    
    return PlatformConfigResponse(
        id=str(config.id),
        platform=config.platform,
        shop_id=config.shop_id,
        shop_name=config.shop_name,
        is_active=config.is_active,
        sync_enabled=config.sync_enabled,
        sync_interval_minutes=config.sync_interval_minutes,
        last_sync_at=config.last_sync_at,
        token_expires_at=config.token_expires_at,
        created_at=config.created_at,
    )


@integrations_router.put("/platforms/{config_id}", response_model=PlatformConfigResponse)
async def update_platform_config(
    config_id: str,
    data: PlatformConfigUpdate,
    db: Session = Depends(get_db),
):
    """Update platform configuration"""
    config = integration_service.update_platform_config(
        db=db,
        config_id=config_id,
        **data.model_dump(exclude_unset=True),
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    return PlatformConfigResponse(
        id=str(config.id),
        platform=config.platform,
        shop_id=config.shop_id,
        shop_name=config.shop_name,
        is_active=config.is_active,
        sync_enabled=config.sync_enabled,
        sync_interval_minutes=config.sync_interval_minutes,
        last_sync_at=config.last_sync_at,
        token_expires_at=config.token_expires_at,
        created_at=config.created_at,
    )


@integrations_router.delete("/platforms/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_config(
    config_id: str,
    db: Session = Depends(get_db),
):
    """Delete platform configuration"""
    success = integration_service.delete_platform_config(db, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Platform config not found")


# ========== Sync Endpoints ==========

@integrations_router.post("/platforms/{config_id}/sync")
async def trigger_sync(
    config_id: str,
    data: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger manual sync for a platform"""
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    from datetime import timedelta
    time_from = datetime.utcnow() - timedelta(hours=data.hours_back)
    
    # Run sync in background
    background_tasks.add_task(
        sync_service.sync_single_platform,
        db, config_id, time_from, None
    )
    
    return {
        "message": "Sync started",
        "platform": config.platform,
        "shop": config.shop_name,
        "hours_back": data.hours_back,
    }


@integrations_router.post("/sync-all")
async def trigger_sync_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger sync for all active platforms"""
    configs = integration_service.get_platform_configs(db, is_active=True)
    active_count = len([c for c in configs if c.sync_enabled])
    
    # Run sync in background
    background_tasks.add_task(sync_service.sync_all_platforms, db)
    
    return {
        "message": "Sync started for all platforms",
        "platforms_count": active_count,
    }


@integrations_router.get("/platforms/{config_id}/sync-history", response_model=List[SyncJobResponse])
async def get_sync_history(
    config_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Get sync job history for a platform"""
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    jobs = integration_service.get_sync_jobs(db, config_id, limit)
    
    return [
        SyncJobResponse(
            id=str(j.id),
            job_type=j.job_type,
            status=j.status,
            started_at=j.started_at,
            finished_at=j.finished_at,
            orders_fetched=j.orders_fetched,
            orders_created=j.orders_created,
            orders_updated=j.orders_updated,
            error_message=j.error_message,
        )
        for j in jobs
    ]


# ========== OAuth Endpoints ==========

@integrations_router.get("/platforms/{config_id}/auth-url")
async def get_auth_url(
    config_id: str,
    redirect_uri: str,
    db: Session = Depends(get_db),
):
    """Get OAuth authorization URL for a platform"""
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    client = integration_service.get_client_for_config(config)
    auth_url = await client.get_auth_url(redirect_uri)
    
    return {"auth_url": auth_url}


@integrations_router.post("/platforms/{config_id}/exchange-token")
async def exchange_token(
    config_id: str,
    code: str,
    db: Session = Depends(get_db),
):
    """Exchange authorization code for access token"""
    config = integration_service.get_platform_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Platform config not found")
    
    client = integration_service.get_client_for_config(config)
    
    try:
        result = await client.exchange_code_for_token(code)
        
        # Update tokens in database
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        
        integration_service.update_tokens(
            db=db,
            config_id=config_id,
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            expires_at=expires_at,
        )
        
        return {"message": "Token exchanged successfully", "expires_at": expires_at}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
