"""
Web Router - HTML Page Routes
"""
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os

from app.core import get_db, settings
from app.services import OrderService, integration_service

web_router = APIRouter(tags=["Web"])

# Setup templates
templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_path)

# Add datetime to all templates
def get_template_context(request: Request, **kwargs):
    return {"request": request, "now": datetime.now, **kwargs}

@web_router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard - Overview page"""
    stats = OrderService.get_dashboard_stats(db)
    return templates.TemplateResponse("dashboard.html", get_template_context(
        request, 
        title="Dashboard",
        stats=stats
    ))

@web_router.get("/orders")
async def orders_list(request: Request, db: Session = Depends(get_db)):
    """Orders List page"""
    return templates.TemplateResponse("orders/list.html", get_template_context(
        request,
        title="จัดการออเดอร์"
    ))

@web_router.get("/orders/create")
async def orders_create(request: Request, db: Session = Depends(get_db)):
    """Create Order page"""
    return templates.TemplateResponse("orders/create.html", get_template_context(
        request,
        title="สร้างออเดอร์"
    ))

@web_router.get("/orders/{order_id}")
async def order_detail(request: Request, order_id: str, db: Session = Depends(get_db)):
    """Order Detail page"""
    return templates.TemplateResponse("orders/detail.html", get_template_context(
        request,
        title="รายละเอียดออเดอร์",
        order_id=order_id
    ))

@web_router.get("/orders/{order_id}/edit")
async def order_edit(request: Request, order_id: str, db: Session = Depends(get_db)):
    """Edit Order page"""
    return templates.TemplateResponse("orders/edit.html", get_template_context(
        request,
        title="แก้ไขออเดอร์",
        order_id=order_id
    ))

@web_router.get("/products")
async def products_list(request: Request, db: Session = Depends(get_db)):
    """Products List page"""
    return templates.TemplateResponse("products/list.html", get_template_context(
        request,
        title="จัดการสินค้า"
    ))

@web_router.get("/stock")
async def stock_page(request: Request, db: Session = Depends(get_db)):
    """Stock Management page"""
    return templates.TemplateResponse("stock/index.html", get_template_context(
        request,
        title="บริหารสต๊อก"
    ))

@web_router.get("/packing")
async def packing_page(request: Request, db: Session = Depends(get_db)):
    """Packing page"""
    return templates.TemplateResponse("packing/index.html", get_template_context(
        request,
        title="แพ็คสินค้า"
    ))

@web_router.get("/promotions")
async def promotions_page(request: Request, db: Session = Depends(get_db)):
    """Promotions page"""
    return templates.TemplateResponse("promotions/list.html", get_template_context(
        request,
        title="โปรโมชั่น"
    ))

@web_router.get("/finance")
async def finance_page(request: Request, db: Session = Depends(get_db)):
    """Finance page"""
    return templates.TemplateResponse("finance/index.html", get_template_context(
        request,
        title="การเงิน"
    ))


# ========== Settings Pages ==========

@web_router.get("/settings")
async def settings_page(request: Request):
    """Settings redirect to integrations"""
    return RedirectResponse(url="/settings/integrations")


@web_router.get("/settings/integrations")
async def settings_integrations(request: Request, db: Session = Depends(get_db)):
    """Platform Integrations settings page"""
    platforms = integration_service.get_platform_configs(db)
    
    # Build webhook base URL
    webhook_base_url = f"https://weorder.jlcgroup.co"
    
    return templates.TemplateResponse("settings/integrations.html", {
        "request": request,
        "title": "Platform Integrations",
        "platforms": platforms,
        "webhook_base_url": webhook_base_url,
        "now": datetime.now(),
    })
