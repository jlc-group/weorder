"""
API Router - JSON Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core import get_db
from app.models import (
    OrderHeader, OrderItem, Product, Warehouse, Company, SalesChannel,
    StockLedger, Promotion, PromotionAction, PrepackBox, PaymentReceipt,
    PaymentAllocation
)
from app.services import OrderService, ProductService, StockService, PromotionService
from app.schemas.order import OrderCreate, OrderUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.stock import StockMovementCreate

# Import sub-routers
from app.api.webhooks import webhook_router
from app.api.integrations import integrations_router

api_router = APIRouter(tags=["API"])

# Include sub-routers
api_router.include_router(webhook_router)
api_router.include_router(integrations_router)

# ===================== HEALTH & STATUS =====================

@api_router.get("/status")
async def api_status():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.now().isoformat()}

# ===================== DASHBOARD =====================

@api_router.get("/dashboard/stats")
async def dashboard_stats(db: Session = Depends(get_db)):
    return OrderService.get_dashboard_stats(db)

# ===================== ORDERS =====================

@api_router.get("/orders")
async def list_orders(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    orders, total = OrderService.get_orders(db, channel, status, search, page, per_page)
    return {
        "orders": [
            {
                "id": str(o.id),
                "external_order_id": o.external_order_id,
                "channel_code": o.channel_code,
                "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "total_amount": float(o.total_amount or 0),
                "status_normalized": o.status_normalized,
                "payment_status": o.payment_status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "items": [
                    {
                        "id": str(item.id),
                        "sku": item.sku,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price or 0),
                        "line_total": float(item.line_total or 0),
                        "line_type": item.line_type
                    }
                    for item in o.items
                ]
            }
            for o in orders
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, db: Session = Depends(get_db)):
    try:
        order = OrderService.get_order_by_id(db, UUID(order_id))
    except:
        order = OrderService.get_order_by_external_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": str(order.id),
        "external_order_id": order.external_order_id,
        "channel_code": order.channel_code,
        "company_id": str(order.company_id) if order.company_id else None,
        "warehouse_id": str(order.warehouse_id) if order.warehouse_id else None,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "status_normalized": order.status_normalized,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "shipping_method": order.shipping_method,
        "subtotal_amount": float(order.subtotal_amount or 0),
        "discount_amount": float(order.discount_amount or 0),
        "shipping_fee": float(order.shipping_fee or 0),
        "total_amount": float(order.total_amount or 0),
        "order_datetime": order.order_datetime.isoformat() if order.order_datetime else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "id": str(item.id),
                "sku": item.sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price or 0),
                "line_discount": float(item.line_discount or 0),
                "line_total": float(item.line_total or 0),
                "line_type": item.line_type
            }
            for item in order.items
        ]
    }

@api_router.post("/orders")
async def create_order(order_data: dict, db: Session = Depends(get_db)):
    # Get default company
    company = db.query(Company).first()
    if not company:
        # Create default company
        company = Company(code="JLC", name="JLC Group")
        db.add(company)
        db.commit()
        db.refresh(company)
    
    # Create order
    order_create = OrderCreate(
        channel_code=order_data.get("channel_code", "manual"),
        company_id=company.id,
        warehouse_id=order_data.get("warehouse_id"),
        customer_name=order_data.get("customer_name"),
        customer_phone=order_data.get("customer_phone"),
        customer_address=order_data.get("customer_address"),
        payment_method=order_data.get("payment_method"),
        shipping_method=order_data.get("shipping_method"),
        shipping_fee=order_data.get("shipping_fee", 0),
        discount_amount=order_data.get("discount_amount", 0),
        items=[
            {
                "product_id": item.get("product_id"),
                "sku": item.get("sku"),
                "product_name": item.get("product_name"),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0),
                "line_discount": item.get("line_discount", 0),
                "line_type": item.get("line_type", "NORMAL")
            }
            for item in order_data.get("items", [])
        ]
    )
    
    order = OrderService.create_order(db, order_create)
    
    # Apply promotions for internal channels
    if order.channel_code in ["manual", "facebook", "line"]:
        PromotionService.apply_promotions_to_order(db, order)
    
    return {"id": str(order.id), "external_order_id": order.external_order_id}

@api_router.post("/orders/{order_id}/status")
async def update_order_status(order_id: str, data: dict, db: Session = Depends(get_db)):
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    try:
        order_uuid = UUID(order_id)
    except:
        order = OrderService.get_order_by_external_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order_uuid = order.id
    
    success, message = OrderService.update_status(db, order_uuid, new_status)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}

@api_router.get("/orders/{order_id}/label")
async def get_order_label(order_id: str, db: Session = Depends(get_db)):
    try:
        order = OrderService.get_order_by_id(db, UUID(order_id))
    except:
        order = OrderService.get_order_by_external_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Generate simple label HTML
    items_html = "".join([
        f"<div>{item.sku} x {item.quantity}</div>"
        for item in order.items
    ])
    
    return f"""
    <div style="border: 2px solid #000; padding: 20px; max-width: 400px;">
        <h3 style="margin: 0 0 10px 0;">ใบปะหน้าพัสดุ</h3>
        <div style="font-size: 18px; font-weight: bold;">{order.external_order_id or str(order.id)[:8]}</div>
        <hr>
        <div><strong>ลูกค้า:</strong> {order.customer_name or '-'}</div>
        <div><strong>เบอร์:</strong> {order.customer_phone or '-'}</div>
        <div><strong>ที่อยู่:</strong> {order.customer_address or '-'}</div>
        <hr>
        <div><strong>รายการ:</strong></div>
        {items_html}
        <hr>
        <div style="font-size: 12px;">วันที่พิมพ์: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """

# ===================== PRODUCTS =====================

@api_router.get("/products")
async def list_products(
    product_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    products, total = ProductService.get_products(db, product_type, search, True, page, per_page)
    return {
        "products": [
            {
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "product_type": p.product_type,
                "standard_cost": float(p.standard_cost or 0),
                "standard_price": float(p.standard_price or 0),
                "image_url": p.image_url,
                "is_active": p.is_active
            }
            for p in products
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }

@api_router.post("/products")
async def create_product(data: dict, db: Session = Depends(get_db)):
    product_data = ProductCreate(
        sku=data.get("sku"),
        name=data.get("name"),
        description=data.get("description"),
        product_type=data.get("product_type", "NORMAL"),
        standard_cost=data.get("standard_cost", 0),
        standard_price=data.get("standard_price", 0),
        image_url=data.get("image_url")
    )
    
    product = ProductService.create_product(db, product_data)
    return {"id": str(product.id), "sku": product.sku}

@api_router.put("/products/{product_id}")
async def update_product(product_id: str, data: dict, db: Session = Depends(get_db)):
    product_data = ProductUpdate(**{k: v for k, v in data.items() if v is not None})
    product = ProductService.update_product(db, UUID(product_id), product_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": str(product.id), "sku": product.sku}

# ===================== WAREHOUSES =====================

@api_router.get("/warehouses")
async def list_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
    return [
        {"id": str(w.id), "code": w.code, "name": w.name}
        for w in warehouses
    ]

# ===================== STOCK =====================

@api_router.get("/stock/summary")
async def stock_summary(
    warehouse_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    wh_id = UUID(warehouse_id) if warehouse_id else None
    return StockService.get_stock_summary(db, wh_id, search)

@api_router.get("/stock/movements")
async def stock_movements(
    warehouse_id: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    wh_id = UUID(warehouse_id) if warehouse_id else None
    movements = StockService.get_recent_movements(db, wh_id, movement_type, limit)
    
    return [
        {
            "id": str(m.id),
            "warehouse_id": str(m.warehouse_id),
            "product_id": str(m.product_id),
            "sku": m.product.sku if m.product else None,
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "reference_type": m.reference_type,
            "note": m.note,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in movements
    ]

@api_router.post("/stock/movements")
async def add_stock_movement(data: dict, db: Session = Depends(get_db)):
    movement_data = StockMovementCreate(
        warehouse_id=UUID(data.get("warehouse_id")),
        product_id=UUID(data.get("product_id")),
        movement_type=data.get("movement_type"),
        quantity=data.get("quantity"),
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        note=data.get("note")
    )
    
    movement = StockService.add_stock_movement(db, movement_data)
    return {"id": str(movement.id)}

# ===================== PROMOTIONS =====================

@api_router.get("/promotions")
async def list_promotions(
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    promotions = PromotionService.get_promotions(db, active_only)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "condition_type": p.condition_type,
            "condition_json": p.condition_json,
            "channel_filter": p.channel_filter,
            "priority": p.priority,
            "start_at": p.start_at.isoformat() if p.start_at else None,
            "end_at": p.end_at.isoformat() if p.end_at else None,
            "is_active": p.is_active,
            "actions": [
                {
                    "action_type": a.action_type,
                    "free_product_id": str(a.free_product_id) if a.free_product_id else None,
                    "free_sku": a.free_sku,
                    "free_quantity": a.free_quantity
                }
                for a in p.actions
            ]
        }
        for p in promotions
    ]

@api_router.post("/promotions")
async def create_promotion(data: dict, db: Session = Depends(get_db)):
    promotion = PromotionService.create_promotion(
        db,
        name=data.get("name"),
        condition_type=data.get("condition_type"),
        condition_json=data.get("condition_json", {}),
        actions=data.get("actions", []),
        channel_filter=data.get("channel_filter"),
        priority=data.get("priority", 0),
        start_at=data.get("start_at"),
        end_at=data.get("end_at")
    )
    return {"id": str(promotion.id)}

@api_router.post("/promotions/{promotion_id}/toggle")
async def toggle_promotion(promotion_id: str, db: Session = Depends(get_db)):
    promotion = PromotionService.toggle_promotion(db, UUID(promotion_id))
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"id": str(promotion.id), "is_active": promotion.is_active}

# ===================== PREPACK BOXES =====================

@api_router.get("/prepack-boxes")
async def list_prepack_boxes(db: Session = Depends(get_db)):
    boxes = db.query(PrepackBox).order_by(PrepackBox.created_at.desc()).limit(100).all()
    return [
        {
            "box_uid": box.box_uid,
            "set_sku": box.set_product_id,
            "warehouse_name": box.warehouse.name if box.warehouse else None,
            "status": box.status,
            "created_at": box.created_at.isoformat() if box.created_at else None
        }
        for box in boxes
    ]

# ===================== PAYMENTS =====================

@api_router.post("/payments")
async def create_payment(data: dict, db: Session = Depends(get_db)):
    order_id = UUID(data.get("order_id"))
    amount = data.get("amount")
    
    order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create payment receipt
    receipt = PaymentReceipt(
        payment_method=data.get("payment_method", "TRANSFER"),
        amount=amount,
        note=data.get("note"),
        status="FULL"
    )
    db.add(receipt)
    db.flush()
    
    # Create allocation
    allocation = PaymentAllocation(
        receipt_id=receipt.id,
        order_id=order_id,
        amount=amount
    )
    db.add(allocation)
    
    # Update order payment status
    total_paid = sum(a.amount for a in order.payments) + amount
    if total_paid >= order.total_amount:
        order.payment_status = "PAID"
        order.status_normalized = "PAID"
    else:
        order.payment_status = "PARTIAL"
    
    db.commit()
    
    return {"id": str(receipt.id)}
