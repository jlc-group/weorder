"""
API Router - JSON Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
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
from app.services import OrderService, ProductService, StockService, PromotionService, integration_service
from app.schemas.order import OrderCreate, OrderUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.stock import StockMovementCreate
from app.schemas.return_schema import ReturnRequest

# Import sub-routers
from app.api.webhooks import webhook_router
from app.api.integrations import integrations_router
from app.api.invoice_request import invoice_request_router
from app.api.invoice_request import invoice_request_router
from app.api.finance import finance_router
from app.api.prepack import router as prepack_router
from app.api.reporting import router as reporting_router
from app.api.product_set import router as product_set_router
from app.api.endpoints import listings as listings_router

api_router = APIRouter(tags=["API"])

# Include sub-routers
api_router.include_router(webhook_router)
api_router.include_router(integrations_router)
api_router.include_router(invoice_request_router)
api_router.include_router(finance_router)
api_router.include_router(prepack_router)
api_router.include_router(reporting_router)
api_router.include_router(product_set_router)
api_router.include_router(listings_router.router, prefix="/listings", tags=["listings"])

from app.api.sync import router as sync_router
api_router.include_router(sync_router)



# ===================== HEALTH & STATUS =====================

@api_router.get("/status")
def api_status():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.now().isoformat()}

# ===================== DASHBOARD =====================

@api_router.get("/dashboard/stats")
def dashboard_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return OrderService.get_dashboard_stats(db, start_date=start_date, end_date=end_date)

# ===================== ORDERS =====================

@api_router.get("/orders")
def list_orders(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    orders, total = OrderService.get_orders(
        db, channel, status, search, start_date, end_date, page, per_page
    )
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
                "payment_status": o.payment_status or ("PAID" if o.status_normalized in ["PAID", "PACKING", "SHIPPED", "DELIVERED", "COMPLETED"] else "PENDING"),
                "courier_code": o.courier_code or ((o.raw_payload or {}).get("packages") or [{}])[0].get("shipping_provider_name") or "-",
                "tracking_number": o.tracking_number or ((o.raw_payload or {}).get("packages") or [{}])[0].get("tracking_number") or "",
                "order_datetime": o.order_datetime.isoformat() if o.order_datetime else None,
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

    return HTMLResponse(content=page_html)

@api_router.get("/orders/sku-summary")
def get_sku_summary(
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get summarized SKU counts for filter options"""
    return OrderService.get_sku_summary(
        db,
        channel=channel,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date
    )

@api_router.post("/orders/batch-status")
def batch_update_status(data: dict, db: Session = Depends(get_db)):
    """
    Batch update order status.
    Supports either list of 'ids' OR filters ('filter_status', 'filter_channel', etc.)
    """
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="New status is required")
        
    ids = data.get("ids", [])
    
    # Extract filters
    channel = data.get("filter_channel")
    current_status = data.get("filter_status")
    search = data.get("search")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    
    count, message = OrderService.batch_update_status(
        db, 
        new_status=new_status,
        channel=channel, 
        current_status=current_status,
        search=search, 
        start_date=start_date, 
        end_date=end_date, 
        order_ids=ids
    )
    
    return {"success": True, "count": count, "message": message}

@api_router.post("/orders/arrange-shipment")
async def arrange_shipment(data: dict, db: Session = Depends(get_db)):
    """
    Arrange Shipment (RTS) for orders
    Input: { "ids": ["id1", "id2"] }
    """
    ids = data.get("ids", [])
    if not ids:
        return {"success": False, "message": "No IDs provided"}
        
    success_count, results = await OrderService.batch_arrange_shipment(db, ids)
    
    return {
        "success": True,
        "count": success_count,
        "results": results,
        "message": f"Successfully arranged shipment for {success_count} orders"
    }

@api_router.post("/orders/{id}/return")
def return_order(
    id: UUID, 
    return_req: ReturnRequest, 
    db: Session = Depends(get_db)
):
    """
    Process Return for an Order
    """
    # Convert Pydantic items to dicts
    items_dict = [item.model_dump() for item in return_req.items]
    
    try:
        success = StockService.process_return(db, id, items_dict, return_req.note)
        return {"success": success, "message": "Return processed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log error
        print(f"Return Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error processing return")

# IMPORTANT: Static routes must come BEFORE dynamic routes
@api_router.get("/orders/batch-labels")
async def get_batch_labels(
    ids: Optional[str] = Query(None, description="Comma-separated order IDs"),
    filter_channel: Optional[str] = Query(None),
    filter_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("html", description="Output format: html or pdf"),
    db: Session = Depends(get_db)
):
    """Generate printable page with multiple labels (HTML or PDF)"""
    from fastapi.responses import HTMLResponse, Response
    from app.services.label_service import LabelService
    
    order_ids = []
    if ids:
        order_ids = [id.strip() for id in ids.split(',') if id.strip()]
    else:
        # Resolve IDs from filters
        # Use a temporary query helper or just re-implement query logic here?
        # Reuse logic via extracting IDs from OrderService.get_orders or similar?
        # Actually, let's use a simple query here since we just need IDs.
        query = db.query(OrderHeader.external_order_id) # Prefer external ID for label service
        
        # Apply filters (Simplified version of OrderService logic)
        if filter_channel and filter_channel != "ALL" and filter_channel != "all":
            query = query.filter(OrderHeader.channel_code == filter_channel)
        if filter_status:
           query = query.filter(OrderHeader.status_normalized == filter_status)
        if search:
            query = query.filter(OrderHeader.external_order_id.ilike(f"%{search}%"))
            
        # Limit to prevent overload
        BATCH_LIMIT = 200
        results = query.limit(BATCH_LIMIT).all()
        order_ids = [r[0] for r in results]
        
        if not order_ids:
             return HTMLResponse("<h1>ไม่พบออเดอร์ตามเงื่อนไข</h1>")

    if not order_ids:
        raise HTTPException(status_code=400, detail="No order IDs provided or found")
    
    # Official PDF Labels
    if format == "pdf":
        try:
            pdf_bytes = await LabelService.generate_batch_labels(db, order_ids)
            if not pdf_bytes:
                return HTMLResponse(
                    "<h1>ไม่สามารถสร้าง PDF ได้</h1>"
                    "<p>สาเหตุที่เป็นไปได้:</p>"
                    "<ul>"
                    "<li>ออเดอร์ยังไม่ได้กด <b>\"เตรียมจัดส่ง (Arrange Shipment)\"</b> บน TikTok</li>"
                    "<li>ออเดอร์ไม่ใช่ของ TikTok</li>"
                    "<li>เกิดข้อผิดพลาดในการเชื่อมต่อ</li>"
                    "</ul>"
                    "<p>คำแนะนำ: โปรดตรวจสอบสถานะออเดอร์ใน TikTok Seller Center ว่าได้กดเตรียมจัดส่งแล้วหรือไม่</p>"
                )
                
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=labels_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
                }
            )
        except Exception as e:
            print(f"Error generating PDF labels: {e}")
            return HTMLResponse(f"<h1>Error generating PDF</h1><p>{str(e)}</p>")

    # Legacy HTML Labels (Fallback)
    labels_html = []
    for order_id in order_ids[:100]:  # Limit to 100 labels per batch
        try:
            try:
                order = OrderService.get_order_by_id(db, UUID(order_id))
            except:
                order = OrderService.get_order_by_external_id(db, order_id)
            
            if not order:
                continue
            
            items_html = "".join([
                f"<div style='margin: 2px 0;'>{item.sku} x {item.quantity}</div>"
                for item in order.items
            ])
            
            label = f"""
            <div style="border: 2px solid #000; padding: 15px; width: 380px; margin: 10px; page-break-inside: avoid; font-family: Arial, sans-serif;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span style="font-size: 12px; color: #666;">{order.channel_code.upper()}</span>
                    <span style="font-size: 12px; color: #666;">#{order.external_order_id or str(order.id)[:8]}</span>
                </div>
                <div style="font-size: 16px; font-weight: bold; margin-bottom: 8px;">{order.customer_name or '-'}</div>
                <div style="font-size: 13px; margin-bottom: 5px;"><strong>📱</strong> {order.customer_phone or '-'}</div>
                <div style="font-size: 12px; margin-bottom: 10px; line-height: 1.4;"><strong>📍</strong> {order.customer_address or '-'}</div>
                <hr style="border: 1px dashed #ccc; margin: 10px 0;">
                <div style="font-size: 12px;"><strong>รายการ:</strong></div>
                <div style="font-size: 13px; margin-top: 5px;">{items_html}</div>
            </div>
            """
            labels_html.append(label)
        except Exception as e:
            print(f"Error generating label for {order_id}: {e}")
            continue
    
    if not labels_html:
        return HTMLResponse("<h1>ไม่พบออเดอร์</h1>")
    
    page_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>ใบปะหน้าพัสดุ ({len(labels_html)} รายการ)</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 0; }}
                .no-print {{ display: none !important; }}
                .label-container {{ display: flex; flex-wrap: wrap; justify-content: flex-start; }}
            }}
            @media screen {{
                body {{ background: #f5f5f5; padding: 20px; }}
                .label-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }}
            }}
            .print-btn {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 30px;
                font-size: 18px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }}
            .print-btn:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">🖨️ พิมพ์ทั้งหมด ({len(labels_html)} ใบ)</button>
        <div class="label-container">
            {"".join(labels_html)}
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=page_html)

@api_router.get("/orders/pick-list")
def get_pick_list(
    ids: str = Query(..., description="Comma-separated order IDs"),
    db: Session = Depends(get_db)
):
    """Generate Pick List (Product Summary)"""
    from fastapi.responses import HTMLResponse
    from app.services.pick_list_service import PickListService
    
    order_ids = [id.strip() for id in ids.split(',') if id.strip()]
    if not order_ids:
        raise HTTPException(status_code=400, detail="No order IDs provided")
        
    try:
        items = PickListService.generate_summary(db, order_ids)
    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{str(e)}</p>")
        
    if not items:
        return HTMLResponse("<h1>ไม่พบสินค้า</h1>")
        
    rows = ""
    total_qty = 0
    for idx, item in enumerate(items, 1):
        components_html = ""
        if item.get("components"):
            comps_list = [f"{c['name']} (x{c['qty']})" for c in item["components"]]
            components_html = f"<div style='font-size: 11px; color: #0d6efd; margin-top: 4px;'>📦 <b>ในชุดประกอบด้วย:</b> {', '.join(comps_list)}</div>"

        rows += f"""
        <tr>
            <td style='text-align: center;'>{idx}</td>
            <td>
                <div style='font-weight: bold;'>{item['sku']}</div>
                <div style='font-size: 12px; color: #666;'>{item['name']}</div>
                {components_html}
            </td>
            <td style='text-align: center; font-size: 18px; font-weight: bold;'>{item['quantity']}</td>
            <td><div style='width: 20px; height: 20px; border: 1px solid #ccc;'></div></td>
        </tr>
        """
        total_qty += item['quantity']
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>ใบสรุปรายการสินค้า (Pick List)</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; }}
            th {{ background-color: #f2f2f2; text-align: left; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .print-btn {{
                position: fixed; top: 20px; right: 20px;
                padding: 10px 20px; background: #28a745; color: white;
                border: none; border-radius: 5px; cursor: pointer; font-size: 16px;
            }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">🖨️ พิมพ์ใบสรุป</button>
        <div class="header">
            <h2>ใบสรุปรายการสินค้า (Pick List)</h2>
            <p>สำหรับ {len(order_ids)} ออเดอร์ | รวมสินค้าทั้งหมด {total_qty} ชิ้น</p>
            <p style="font-size: 12px; color: #666;">พิมพ์เมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px; text-align: center;">#</th>
                    <th>สินค้า</th>
                    <th style="width: 100px; text-align: center;">จำนวน</th>
                    <th style="width: 50px;">Check</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@api_router.get("/orders/sku-summary-thermal")
def sku_summary_thermal(ids: str, db: Session = Depends(get_db)):
    """
    Generate Thermal-Friendly SKU Summary (Shopping List)
    Width: 80mm
    Format: Simple List (SKU x Quantity)
    """
    from fastapi.responses import HTMLResponse
    from app.services.pick_list_service import PickListService
    
    try:
        order_ids = [id.strip() for id in ids.split(",") if id.strip()]
        if not order_ids:
             return HTMLResponse("No orders selected")
            
        # reuse pick list logic as it already aggregates and explodes bundles
        pick_items = PickListService.generate_summary(db, order_ids)
        
        # Generate Thermal HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    width: 72mm; /* Fits 80mm paper with margin */
                    margin: 0;
                    padding: 5px;
                }
                .header {
                    text-align: center;
                    border-bottom: 2px dashed black;
                    padding-bottom: 5px;
                    margin-bottom: 10px;
                }
                .item {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 5px;
                    border-bottom: 1px dotted #ccc;
                    padding-bottom: 2px;
                }
                .qty { font-weight: bold; font-size: 14px; }
                .sku { flex: 1; margin-right: 10px; word-wrap: break-word; }
                .footer {
                    margin-top: 15px;
                    text-align: center;
                    font-size: 10px;
                    border-top: 1px solid black;
                    padding-top: 5px;
                }
                .no-print { display: none; }
                @media print {
                    .no-print { display: none !important; }
                }
                .print-btn {
                    width: 100%;
                    padding: 5px;
                    margin-bottom: 10px;
                    background: #000;
                    color: #fff;
                    border: none;
                    cursor: pointer;
                }
            </style>
        </head>
        <body onload="window.print()">
            <button class="print-btn no-print" onclick="window.print()">Print</button>
            <div class="header">
                <h3>Pick List (Thermal)</h3>
                <p>Orders: """ + str(len(order_ids)) + """</p>
                <p>""" + datetime.now().strftime("%d/%m/%y %H:%M") + """</p>
            </div>
            
            <div class="items">
        """
        
        total_items = 0
        for item in pick_items:
            # Handle bundle components if any (though PickListService might already flatten or nest them)
            # PickListService returns list of dicts. If it has 'components', list them.
            
            html += f"""
            <div class="item">
                <span class="sku">{item['sku']}</span>
                <span class="qty">x {item['quantity']}</span>
            </div>
            """
            
            if item.get("components"):
                for c in item["components"]:
                     html += f"""
                    <div class="item" style="padding-left: 10px; font-size: 10px; color: #555;">
                        <span class="sku">- {c['name']}</span>
                        <span class="qty">x {c['qty']}</span>
                    </div>
                    """
            
            total_items += item['quantity']
            
        html += f"""
            </div>
            
            <div class="footer">
                <p>Total Items: {total_items}</p>
                <p>*** END ***</p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Failed to generate thermal summary: {e}")
        return HTMLResponse(f"Error: {str(e)}", status_code=500)

@api_router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    try:
        order = OrderService.get_order_by_id(db, UUID(order_id))
    except:
        order = OrderService.get_order_by_external_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Extract extra info from raw_payload
    raw = order.raw_payload or {}
    cancellation_reason = raw.get("cancel_reason") or raw.get("cancellation_reason") or "-"
    
    # Try to find payment time
    paid_time = raw.get("paid_time") # TikTok timestamp
    if paid_time:
        try:
            payment_date = datetime.fromtimestamp(int(paid_time)).strftime('%d/%m/%Y %H:%M')
        except:
            payment_date = "-"
    else:
        payment_date = "-"

    return {
        "id": str(order.id),
        "external_order_id": order.external_order_id,
        "channel_code": order.channel_code,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "status_normalized": order.status_normalized,
        "payment_method": order.payment_method or raw.get("payment_method_name") or "-",
        "payment_status": order.payment_status or ("PAID" if order.status_normalized in ["PAID", "PACKING", "SHIPPED", "DELIVERED", "COMPLETED"] else "PENDING"),
        "payment_date": payment_date,
        "cancellation_reason": cancellation_reason,
        "courier_code": order.courier_code or (raw.get("packages") or [{}])[0].get("shipping_provider_name") or "-",
        "tracking_number": order.tracking_number or (raw.get("packages") or [{}])[0].get("tracking_number") or "-",
        "subtotal_amount": float(order.subtotal_amount or 0),
        "discount_amount": float(order.discount_amount or 0),
        "shipping_fee": float(order.shipping_fee or 0),
        "total_amount": float(order.total_amount or 0),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "raw_payload": order.raw_payload,
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
def create_order(order_data: dict, db: Session = Depends(get_db)):
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
def update_order_status(order_id: str, data: dict, db: Session = Depends(get_db)):
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
    
    # --- Try to get platform label ---
    if order.channel_code in ["tiktok", "shopee"]:
        shop_id = (order.raw_payload or {}).get("shop_id")
        
        config = None
        if shop_id:
             config = integration_service.get_platform_config_by_shop(db, order.channel_code, str(shop_id))
        
        if not config:
            # Fallback to any active config for this platform
            configs = integration_service.get_platform_configs(db, platform=order.channel_code, is_active=True)
            if configs:
                config = configs[0]

        if config:
            try:
                client = integration_service.get_client_for_config(config)
                if hasattr(client, "get_shipping_label"):
                    label_url = await client.get_shipping_label(order.external_order_id)
                    if label_url:
                        return RedirectResponse(label_url)
            except Exception as e:
                print(f"Failed to get platform label: {e}")
                # Fallback to internal HTLM
    
    # Generate simple label HTML
    items_html = "".join([
        f"<div>{item.sku} x {item.quantity}</div>"
        for item in order.items
    ])
    
    return f"""
    <div style="border: 2px solid #000; padding: 20px; max-width: 400px;">
        <h3 style="margin: 0 0 10px 0;">ใบปะหน้าพัสดุ (INTERNAL)</h3>
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

@api_router.get("/orders/{order_id}/tax-invoice")
def get_tax_invoice(order_id: str, db: Session = Depends(get_db)):
    """Generate Tax Invoice HTML for an order (only for DELIVERED/COMPLETED orders)"""
    from fastapi.responses import HTMLResponse
    from jinja2 import Environment, FileSystemLoader
    from app.services.invoice_service import InvoiceService
    import os
    
    try:
        order = OrderService.get_order_by_id(db, UUID(order_id))
    except:
        order = OrderService.get_order_by_external_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only allow tax invoice for completed orders
    allowed_statuses = ["DELIVERED", "COMPLETED"]
    if order.status_normalized not in allowed_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"ไม่สามารถออกใบกำกับภาษีได้ - คำสั่งซื้อต้องอยู่ในสถานะ 'จัดส่งสำเร็จ' หรือ 'เสร็จสิ้น' (สถานะปัจจุบัน: {order.status_normalized})"
        )
    invoice_data = InvoiceService.get_invoice_data(db, order.id)
    if not invoice_data:
        raise HTTPException(status_code=500, detail="Failed to generate invoice data")
    
    # Render template
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("tax_invoice.html")
    
    html = template.render(**invoice_data)
    
    return HTMLResponse(content=html)


# ===================== PRODUCTS =====================

@api_router.get("/products")
def list_products(
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
def create_product(data: dict, db: Session = Depends(get_db)):
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
def update_product(product_id: str, data: dict, db: Session = Depends(get_db)):
    product_data = ProductUpdate(**{k: v for k, v in data.items() if v is not None})
    product = ProductService.update_product(db, UUID(product_id), product_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": str(product.id), "sku": product.sku}

@api_router.get("/products/{product_id}/components")
def get_product_components(product_id: str, db: Session = Depends(get_db)):
    """Get components for a SET product"""
    try:
        pid = UUID(product_id)
        components = ProductService.get_set_components(db, pid)
        return [
            {
                "product_id": str(c["product"].id),
                "sku": c["product"].sku,
                "name": c["product"].name,
                "quantity": c["quantity"]
            }
            for c in components
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.put("/products/{product_id}/components")
def update_product_components(product_id: str, data: List[dict], db: Session = Depends(get_db)):
    """
    Update components for a SET product
    Body: List of {"product_id": "uuid", "quantity": 1}
    """
    try:
        pid = UUID(product_id)
        success = ProductService.update_set_components(db, pid, data)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== WAREHOUSES =====================

@api_router.get("/warehouses")
def list_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
    return [
        {"id": str(w.id), "code": w.code, "name": w.name}
        for w in warehouses
    ]

# ===================== STOCK =====================

@api_router.get("/stock/summary")
def stock_summary(
    warehouse_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    wh_id = UUID(warehouse_id) if warehouse_id else None
    return StockService.get_stock_summary(db, wh_id, search)

@api_router.get("/stock/movements")
def stock_movements(
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
def add_stock_movement(data: dict, db: Session = Depends(get_db)):
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
def list_promotions(
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
def create_promotion(data: dict, db: Session = Depends(get_db)):
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
def toggle_promotion(promotion_id: str, db: Session = Depends(get_db)):
    promotion = PromotionService.toggle_promotion(db, UUID(promotion_id))
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"id": str(promotion.id), "is_active": promotion.is_active}

# ===================== PREPACK BOXES =====================

@api_router.get("/prepack-boxes")
def list_prepack_boxes(db: Session = Depends(get_db)):
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
def create_payment(data: dict, db: Session = Depends(get_db)):
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

# ===================== FINANCE =====================

@api_router.get("/finance/summary")
def finance_summary(db: Session = Depends(get_db)):
    from app.services.finance_service import FinanceService
    return FinanceService.get_finance_summary(db)
