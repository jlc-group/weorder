"""
Finance API - Staff endpoints for managing tax invoice requests
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
import os

from app.core import get_db
from app.models import OrderHeader
from app.models.invoice import InvoiceProfile
from app.services.invoice_service import InvoiceService
from app.services.finance_sync_service import FinanceSyncService
from app.models.integration import PlatformConfig
from app.models.finance import MarketplaceTransaction


finance_router = APIRouter(prefix="/finance", tags=["Finance"])


class InvoiceIssue(BaseModel):
    """Request body for issuing an invoice"""
    pass  # No extra fields needed for now


class InvoiceReject(BaseModel):
    """Request body for rejecting an invoice"""
    reason: str


class InvoiceRequestItem(BaseModel):
    """Single invoice request item for list"""
    id: str
    order_id: str
    external_order_id: Optional[str]
    channel_code: Optional[str]
    invoice_name: str
    tax_id: str
    branch: str
    profile_type: str
    status: str
    created_at: str
    order_total: float


@finance_router.get("/invoice-requests")
def list_invoice_requests(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, ISSUED, REJECTED"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all invoice requests for Finance team.
    """
    query = db.query(InvoiceProfile).join(OrderHeader)
    
    if status:
        query = query.filter(InvoiceProfile.status == status.upper())
    
    # Order by created_at descending (newest first)
    query = query.order_by(desc(InvoiceProfile.created_at))
    
    total = query.count()
    profiles = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Count by status
    pending_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "PENDING").count()
    issued_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "ISSUED").count()
    rejected_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "REJECTED").count()
    
    return {
        "requests": [
            {
                "id": str(p.id),
                "order_id": str(p.order_id),
                "external_order_id": p.order.external_order_id if p.order else None,
                "channel_code": p.order.channel_code if p.order else None,
                "invoice_name": p.invoice_name,
                "tax_id": p.tax_id,
                "branch": p.branch,
                "profile_type": p.profile_type,
                "address": ", ".join(filter(None, [
                    p.address_line1,
                    p.address_line2,
                    p.subdistrict,
                    p.district,
                    p.province,
                    p.postal_code
                ])),
                "phone": p.phone,
                "email": p.email,
                "status": p.status,
                "invoice_number": p.invoice_number,
                "invoice_date": p.invoice_date.strftime("%d/%m/%Y") if p.invoice_date else None,
                "created_at": p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else None,
                "order_total": float(p.order.total_amount or 0) if p.order else 0,
                "rejected_reason": p.rejected_reason
            }
            for p in profiles
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "counts": {
            "pending": pending_count,
            "issued": issued_count,
            "rejected": rejected_count
        }
    }


@finance_router.get("/invoice-requests/{request_id}")
def get_invoice_request(request_id: str, db: Session = Depends(get_db)):
    """
    Get details of a single invoice request.
    """
    try:
        profile = db.query(InvoiceProfile).filter(InvoiceProfile.id == UUID(request_id)).first()
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invoice request not found")
    
    order = profile.order
    
    return {
        "id": str(profile.id),
        "order_id": str(profile.order_id),
        "external_order_id": order.external_order_id if order else None,
        "channel_code": order.channel_code if order else None,
        "customer_name": order.customer_name if order else None,
        "profile_type": profile.profile_type,
        "invoice_name": profile.invoice_name,
        "tax_id": profile.tax_id,
        "branch": profile.branch,
        "address_line1": profile.address_line1,
        "address_line2": profile.address_line2,
        "subdistrict": profile.subdistrict,
        "district": profile.district,
        "province": profile.province,
        "postal_code": profile.postal_code,
        "phone": profile.phone,
        "email": profile.email,
        "status": profile.status,
        "invoice_number": profile.invoice_number,
        "invoice_date": profile.invoice_date.isoformat() if profile.invoice_date else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "issued_at": profile.issued_at.isoformat() if profile.issued_at else None,
        "rejected_reason": profile.rejected_reason,
        "order_total": float(order.total_amount or 0) if order else 0,
        "order_items": [
            {
                "sku": item.sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price or 0),
                "line_total": float(item.line_total or 0)
            }
            for item in (order.items if order else [])
        ]
    }


@finance_router.post("/invoice-requests/{request_id}/issue")
def issue_invoice(request_id: str, db: Session = Depends(get_db)):
    """
    Issue a tax invoice for a request.
    Generates invoice number and marks as ISSUED.
    """
    try:
        profile = db.query(InvoiceProfile).filter(InvoiceProfile.id == UUID(request_id)).first()
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invoice request not found")
    
    if profile.status == "ISSUED":
        raise HTTPException(status_code=400, detail="ใบกำกับภาษีนี้ออกแล้ว")
    
    if profile.status == "REJECTED":
        raise HTTPException(status_code=400, detail="คำขอนี้ถูกปฏิเสธแล้ว ไม่สามารถออกใบกำกับได้")
    
    # Generate invoice number
    now = datetime.now()
    invoice_number = InvoiceService.generate_invoice_number(profile.order)
    
    # Update profile
    profile.status = "ISSUED"
    profile.invoice_number = invoice_number
    profile.invoice_date = now
    profile.issued_at = now
    
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "message": f"ออกใบกำกับภาษีเรียบร้อยแล้ว: {invoice_number}",
        "invoice_number": invoice_number,
        "invoice_date": now.strftime("%d/%m/%Y")
    }


@finance_router.post("/invoice-requests/{request_id}/reject")
def reject_invoice(request_id: str, data: InvoiceReject, db: Session = Depends(get_db)):
    """
    Reject an invoice request.
    """
    try:
        profile = db.query(InvoiceProfile).filter(InvoiceProfile.id == UUID(request_id)).first()
    except:
        raise HTTPException(status_code=400, detail="Invalid request ID")
    
    if not profile:
        raise HTTPException(status_code=404, detail="Invoice request not found")
    
    if profile.status == "ISSUED":
        raise HTTPException(status_code=400, detail="ไม่สามารถปฏิเสธได้ เนื่องจากใบกำกับภาษีออกแล้ว")
    
    # Update profile
    profile.status = "REJECTED"
    profile.rejected_reason = data.reason
    profile.rejected_at = datetime.now()
    
    db.commit()
    
    return {
        "success": True,
        "message": "ปฏิเสธคำขอเรียบร้อยแล้ว"
    }


@finance_router.get("/stats")
def finance_stats(db: Session = Depends(get_db)):
    """
    Get finance dashboard statistics.
    """
    pending_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "PENDING").count()
    issued_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "ISSUED").count()
    rejected_count = db.query(InvoiceProfile).filter(InvoiceProfile.status == "REJECTED").count()
    
    # Today's issued
    from datetime import date
    today = date.today()
    today_issued = db.query(InvoiceProfile).filter(
        InvoiceProfile.status == "ISSUED",
        InvoiceProfile.issued_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    return {
        "pending": pending_count,
        "issued": issued_count,
        "rejected": rejected_count,
        "total": pending_count + issued_count + rejected_count,
        "today_issued": today_issued
    }


@finance_router.post("/sync/{platform}")
async def sync_platform_finance(
    platform: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Trigger manual finance sync for a platform.
    """
    platform = platform.lower()
    
    # correct tiktok platform name
    if platform == "tiktok":
        # Check if config exists for generic 'tiktok' or specific shop
        # Usually checking 'tiktok' platform is enough
        pass
        
    configs = db.query(PlatformConfig).filter(
        PlatformConfig.platform == platform,
        PlatformConfig.is_active == True
    ).all()
    
    if not configs:
        raise HTTPException(status_code=404, detail=f"No active configuration found for {platform}")
    
    service = FinanceSyncService(db)
    
    # Time range
    from datetime import timedelta
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    results = {}
    
    for config in configs:
        shop_name = config.shop_name or config.shop_id
        try:
            stats = await service.sync_platform_finance(config, start_time, end_time)
            results[shop_name] = stats
        except Exception as e:
            results[shop_name] = {"error": str(e)}
            
    return {
        "success": True,
        "platform": platform,
        "range_days": days,
        "results": results
    }


@finance_router.get("/transactions")
def list_transactions(
    platform: Optional[str] = None,
    sort: str = Query("date_desc", pattern="^(date_asc|date_desc|amount_asc|amount_desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List marketplace transactions (Money Trail).
    """
    query = db.query(MarketplaceTransaction)
    
    if platform:
        query = query.filter(MarketplaceTransaction.platform == platform.lower())
        
    # Sort
    if sort == "date_desc":
        query = query.order_by(desc(MarketplaceTransaction.transaction_date))
    elif sort == "date_asc":
        query = query.order_by(MarketplaceTransaction.transaction_date)
    elif sort == "amount_desc":
        query = query.order_by(desc(MarketplaceTransaction.amount))
    elif sort == "amount_asc":
        query = query.order_by(MarketplaceTransaction.amount)
        
    total = query.count()
    txs = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "data": [
            {
                "id": str(t.id),
                "platform": t.platform,
                "type": t.transaction_type,
                "amount": float(t.amount),
                "currency": t.currency,
                "date": t.transaction_date.isoformat() if t.transaction_date else None,
                "order_id": str(t.order_id) if t.order_id else None,
                "description": t.description,
                "payout_reference": t.payout_reference
            }
            for t in txs
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@finance_router.get("/performance")
def get_finance_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed financial performance dashboard data.
    Defaults to current month.
    """
    from datetime import datetime, time
    import calendar

    # Default to current month if dates not provided
    today = datetime.now().date()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        # Last day of current month
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

    # Convert to datetime objects for service
    dt_start = datetime.combine(start_date, time.min)
    dt_end = datetime.combine(end_date, time.max)

    from app.services.finance_service import FinanceService
    return FinanceService.get_performance_dashboard(db, dt_start, dt_end)


@finance_router.get("/fee-details")
def get_fee_details(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed fee breakdown from MarketplaceTransaction raw_data.
    Returns itemized fees like TikTok statement format.
    """
    from datetime import datetime, time
    from sqlalchemy import func, text
    import calendar
    
    # Default to current month
    today = datetime.now().date()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)
    
    dt_start = datetime.combine(start_date, time.min)
    dt_end = datetime.combine(end_date, time.max)
    
    # Fee breakdown structure
    fee_breakdown = {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "platforms": {}
    }
    
    # TikTok - Query from raw_data with detailed fields
    try:
        tiktok_result = db.execute(text("""
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(CAST(raw_data->>'platform_commission_amount' AS NUMERIC)), 0) as platform_commission,
                COALESCE(SUM(CAST(raw_data->>'affiliate_commission_amount' AS NUMERIC)), 0) as affiliate_commission,
                COALESCE(SUM(CAST(raw_data->>'affiliate_ads_commission_amount' AS NUMERIC)), 0) as affiliate_ads_commission,
                COALESCE(SUM(CAST(raw_data->>'affiliate_partner_commission_amount' AS NUMERIC)), 0) as affiliate_partner_commission,
                COALESCE(SUM(CAST(raw_data->>'actual_shipping_fee_amount' AS NUMERIC)), 0) as actual_shipping_fee,
                COALESCE(SUM(CAST(raw_data->>'platform_shipping_fee_discount_amount' AS NUMERIC)), 0) as platform_shipping_discount,
                COALESCE(SUM(CAST(raw_data->>'referral_fee_amount' AS NUMERIC)), 0) as referral_fee,
                COALESCE(SUM(CAST(raw_data->>'retail_delivery_fee_amount' AS NUMERIC)), 0) as retail_delivery_fee,
                COALESCE(SUM(CAST(raw_data->>'fbt_fulfillment_fee_amount' AS NUMERIC)), 0) as fbt_fee,
                COALESCE(SUM(CAST(raw_data->>'fee_amount' AS NUMERIC)), 0) as total_fee,
                COALESCE(SUM(CAST(raw_data->>'gross_sales_amount' AS NUMERIC)), 0) as gross_sales,
                COALESCE(SUM(CAST(raw_data->>'settlement_amount' AS NUMERIC)), 0) as settlement
            FROM marketplace_transaction
            WHERE platform = 'tiktok' 
              AND transaction_type = 'ORDER'
              AND transaction_date >= :start_date 
              AND transaction_date <= :end_date
        """), {"start_date": dt_start, "end_date": dt_end}).first()
        
        if tiktok_result:
            fee_breakdown["platforms"]["tiktok"] = {
                "platform_name": "TikTok Shop",
                "order_count": int(tiktok_result.order_count or 0),
                "gross_sales": float(tiktok_result.gross_sales or 0),
                "total_fees": float(tiktok_result.total_fee or 0),
                "settlement": float(tiktok_result.settlement or 0),
                "details": [
                    {"name": "ค่าคอมมิชชั่น TikTok Shop", "amount": float(tiktok_result.platform_commission or 0)},
                    {"name": "ค่าคอมมิชชั่น Affiliate", "amount": float(tiktok_result.affiliate_commission or 0)},
                    {"name": "ค่าคอมมิชชั่น Affiliate Ads", "amount": float(tiktok_result.affiliate_ads_commission or 0)},
                    {"name": "ค่าคอมมิชชั่นพันธมิตร", "amount": float(tiktok_result.affiliate_partner_commission or 0)},
                    {"name": "ค่าส่งที่ร้านค้าจ่ายจริง", "amount": float(tiktok_result.actual_shipping_fee or 0)},
                    {"name": "ส่วนลดค่าส่งจาก Platform", "amount": float(tiktok_result.platform_shipping_discount or 0)},
                    {"name": "ค่า Referral Fee", "amount": float(tiktok_result.referral_fee or 0)},
                    {"name": "ค่า Retail Delivery", "amount": float(tiktok_result.retail_delivery_fee or 0)},
                    {"name": "ค่า FBT Fulfillment", "amount": float(tiktok_result.fbt_fee or 0)},
                ]
            }
    except Exception as e:
        print(f"Error fetching TikTok fee details: {e}")
    
    # Shopee - Query from transaction_type breakdown
    try:
        shopee_txs = db.query(
            MarketplaceTransaction.transaction_type,
            func.sum(MarketplaceTransaction.amount).label("total")
        ).filter(
            MarketplaceTransaction.platform == 'shopee',
            MarketplaceTransaction.transaction_date >= dt_start,
            MarketplaceTransaction.transaction_date <= dt_end
        ).group_by(MarketplaceTransaction.transaction_type).all()
        
        shopee_order_count = db.query(func.count(MarketplaceTransaction.id)).filter(
            MarketplaceTransaction.platform == 'shopee',
            MarketplaceTransaction.transaction_type == 'ORDER',
            MarketplaceTransaction.transaction_date >= dt_start,
            MarketplaceTransaction.transaction_date <= dt_end
        ).scalar() or 0
        
        if shopee_txs:
            details = []
            total_fees = 0
            gross_revenue = 0
            for tx_type, amount in shopee_txs:
                amt = float(amount or 0)
                if tx_type == 'COMMISSION_FEE':
                    details.append({"name": "ค่าคอมมิชชั่น Shopee", "amount": amt})
                    total_fees += amt
                elif tx_type == 'SERVICE_FEE':
                    details.append({"name": "ค่าบริการ Shopee", "amount": amt})
                    total_fees += amt
                elif tx_type == 'TRANSACTION_FEE':
                    details.append({"name": "ค่าธุรกรรม", "amount": amt})
                    total_fees += amt
                elif tx_type == 'PAYMENT_FEE':
                    details.append({"name": "ค่าชำระเงิน", "amount": amt})
                    total_fees += amt
                elif tx_type == 'SHIPPING_FEE':
                    details.append({"name": "ค่าขนส่ง", "amount": amt})
                    total_fees += amt
                elif tx_type == 'ITEM_PRICE':
                    gross_revenue = amt
                    
            fee_breakdown["platforms"]["shopee"] = {
                "platform_name": "Shopee",
                "order_count": int(shopee_order_count),
                "gross_sales": gross_revenue,
                "total_fees": total_fees,
                "details": details
            }
    except Exception as e:
        print(f"Error fetching Shopee fee details: {e}")
    
    # Lazada - Similar approach
    try:
        lazada_txs = db.query(
            MarketplaceTransaction.transaction_type,
            func.sum(MarketplaceTransaction.amount).label("total")
        ).filter(
            MarketplaceTransaction.platform == 'lazada',
            MarketplaceTransaction.transaction_date >= dt_start,
            MarketplaceTransaction.transaction_date <= dt_end
        ).group_by(MarketplaceTransaction.transaction_type).all()
        
        if lazada_txs:
            details = []
            total_fees = 0
            for tx_type, amount in lazada_txs:
                amt = float(amount or 0)
                if tx_type in ['COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 'PAYMENT_FEE', 'SHIPPING_FEE']:
                    details.append({"name": tx_type.replace("_", " ").title(), "amount": amt})
                    total_fees += amt
                    
            fee_breakdown["platforms"]["lazada"] = {
                "platform_name": "Lazada",
                "total_fees": total_fees,
                "details": details
            }
    except Exception as e:
        print(f"Error fetching Lazada fee details: {e}")
    
    # Calculate totals
    total_all_fees = sum(
        p.get("total_fees", 0) 
        for p in fee_breakdown["platforms"].values()
    )
    fee_breakdown["total_fees"] = total_all_fees
    
    return fee_breakdown


@finance_router.get("/profit/{order_id}")

def get_order_profit_breakdown(order_id: str, db: Session = Depends(get_db)):
    """
    Get detailed financial breakdown (Money Trail) for a specific order.
    Shows the journey from customer payment to actual income.
    """
    try:
        order = db.query(OrderHeader).filter(OrderHeader.id == UUID(order_id)).first()
    except:
        raise HTTPException(status_code=400, detail="Invalid order ID")
        
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Get all transactions for this order
    txs = db.query(MarketplaceTransaction).filter(
        MarketplaceTransaction.order_id == order.id
    ).all()
    
    breakdown = {
        "external_order_id": order.external_order_id,
        "platform": order.channel_code,
        "status": order.status_normalized,
        "revenue": {
            "subtotal": float(order.subtotal_amount or 0),
            "shipping_fee_paid_by_customer": float(order.shipping_fee or 0),
            "platform_discount": float(order.platform_discount_amount or 0),
            "total_gross_revenue": float((order.subtotal_amount or 0) + (order.platform_discount_amount or 0))
        },
        "deductions": [],
        "total_deductions": 0,
        "net_income": 0
    }
    
    total_deductions = 0
    for tx in txs:
        amt = float(tx.amount)
        if tx.transaction_type in ['COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 'PAYMENT_FEE', 'SHIPPING_FEE', 'ADJUSTMENT']:
            breakdown["deductions"].append({
                "type": tx.transaction_type,
                "amount": amt,
                "description": tx.description
            })
            total_deductions += amt
        elif tx.transaction_type == 'ITEM_PRICE':
            # This is already covered in subtotal usually
            pass
            
    breakdown["total_deductions"] = total_deductions
    # Net income from platform perspective is usually subtotal + platform_discount - fees
    breakdown["net_income"] = breakdown["revenue"]["total_gross_revenue"] + total_deductions
    
    return breakdown


@finance_router.get("/profitability")
def get_order_profitability(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db)
):
    from app.services.finance_service import FinanceService
    service = FinanceService()
    return service.get_order_profitability(db, start_date, end_date)


@finance_router.get("/export")
def export_finance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Export finance report - DETAILED BREAKDOWN (Matching TikTok Statement)
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    from sqlalchemy.orm import joinedload
    from app.models import OrderHeader, OrderItem, Product
    from app.models.finance import MarketplaceTransaction
    from collections import defaultdict
    
    # Query Orders with Items, Product, and Linked Transactions
    dt_start = datetime.combine(start_date, datetime.min.time())
    dt_end = datetime.combine(end_date, datetime.max.time())
    
    # We query OrderHeader and join everything needed
    orders = db.query(OrderHeader).options(
        joinedload(OrderHeader.items).joinedload(OrderItem.product)
    ).filter(
        OrderHeader.order_datetime >= dt_start,
        OrderHeader.order_datetime <= dt_end,
        OrderHeader.status_normalized != 'CANCELLED'
    ).order_by(OrderHeader.order_datetime).all()
    
    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Detailed Headers matching the screenshot concept
    headers = [
        "วันที่",
        "Platform", 
        "หมายเลขออเดอร์",
        "สินค้า",
        "ยอดขาย (Gross Sales)",
        "ค่าส่งที่เก็บลูกค้า",
        "ส่วนลด Platform Support",
        "รวมรายรับ (Total Revenue)",
        
        # Deductions
        "ค่าคอมมิชชั่น (Commission)",
        "ค่าธรรมเนียมคำสั่งซื้อ (Transaction Fee)",
        "ค่าธรรมเนียมบริการ (Service Fee)",
        "ค่าส่งที่ร้านจ่ายจริง (Shipping Cost)",
        "ค่าคอม Affiliate",
        "รวมค่าธรรมเนียม (Total Fees)",
        
        # Result
        "ต้นทุนสินค้า (COGS)",
        "กำไรสุทธิ (Net Profit)",
        "ยอดเงินเข้าบัญชี (Payout)"
    ]
    writer.writerow(headers)
    
    for order in orders:
        # Basic Info
        order_date = order.order_datetime.strftime("%Y-%m-%d") if order.order_datetime else ""
        platform = order.channel_code or "Unknown"
        order_id = order.external_order_id or order.order_number or str(order.id)
        
        # Items & COGS
        items_list = []
        cogs = 0.0
        for item in order.items:
            sku = item.sku or "N/A"
            qty = item.quantity or 0
            items_list.append(f"{sku} x{qty}")
            if item.product:
                cost = float(item.product.standard_cost or 0)
                cogs += cost * qty
        items_str = ", ".join(items_list)
        
        # Find associated finance transaction for this order (if synced)
        # This is where we get the REAL numbers from platforms
        txs = db.query(MarketplaceTransaction).filter(
            MarketplaceTransaction.order_id == order.id
        ).all()
        
        # Initialize Values
        gross_sales = float(order.subtotal_amount or 0)
        shipping_income = float(order.shipping_fee or 0)
        platform_discount = float(order.platform_discount_amount or 0)
        
        # Fee buckets
        commission = 0.0
        transaction_fee = 0.0
        service_fee = 0.0
        shipping_cost = 0.0
        affiliate_cost = 0.0
        other_fees = 0.0
        
        payout_amount = 0.0
        
        if txs:
            # Calculate actuals from Money Trail
            # Note: Logic here depends on how we mapped types during sync
            for tx in txs:
                amt = float(tx.amount) # usually negative for fees
                t_type = tx.transaction_type
                raw = tx.raw_data or {}
                
                if t_type == 'COMMISSION_FEE':
                    commission += abs(amt)
                elif t_type == 'TRANSACTION_FEE':
                    transaction_fee += abs(amt)
                elif t_type == 'SERVICE_FEE':
                    service_fee += abs(amt)
                elif t_type == 'SHIPPING_FEE':
                    shipping_cost += abs(amt)
                elif 'affiliate' in (tx.description or "").lower():
                    affiliate_cost += abs(amt)
                elif t_type in ['ADJUSTMENT', 'PAYMENT_FEE']:
                    other_fees += abs(amt)
                
                # --- Platform Specific Field Overrides (More Accurate) ---
                if platform == 'tiktok' and raw:
                    # TikTok keys usually end with _amount
                    # If we find granular keys, we might want to use them instead of generic mapping
                    # But generic mapping is populated from these keys during sync.
                    # Let's trust the generic mapping for now, BUT add Affiliate if missed
                    if 'affiliate_commission_amount' in raw:
                         val = float(raw.get('affiliate_commission_amount') or 0)
                         if val != 0 and affiliate_cost == 0:
                             affiliate_cost += abs(val)

                elif platform == 'shopee' and raw:
                    # Shopee raw_data often contains 'order_income' dict with full breakdown
                    income_data = raw.get('order_income', {})
                    if income_data:
                        # If this transaction holds the full breakdown (usually COMMISSION_FEE type has proper keys)
                        # We might double count if we iterate multiple transactions for same order.
                        # BE CAREFUL.
                        # However, commonly Shopee has multiple rows: one for shipping, one for fee, etc? 
                        # OR one big row? 
                        # Based on sample, COMMISSION_FEE row had 'order_income' with ALL fields.
                        # If we have multiple rows having same 'order_income', we shouldn't sum them up.
                        # Strategy: Only parse specific keys if the current transaction TYPE matches the bucket
                        # OR (Better for Shopee): relying on the generic types we already mapped during Sync might be safer
                        # Sync service ALREADY exploded these into rows. checking SyncService...
                        # Yes, sync service loops fee_mapping and creates rows.
                        # So 'commission += abs(amt)' above should already work!
                        
                        # Just double check Affiliate (AMS)
                        if 'ams_commission_fee' in income_data:
                            val = float(income_data.get('ams_commission_fee') or 0)
                            # Only add if we haven't captured it via generic types
                            # Sync service likely didn't map 'ams_commission_fee' to a specific type?
                            # Checked sync code: 'ams' was not in fee_mapping list.
                            # So we likely missed it or it went to 'UNKNOWN'.
                            if val > 0:
                                # Start fresh for affiliate if not found
                                # But wait, is this per row or global for order? 
                                # 'order_income' is Order Level data attached to a specific transaction record.
                                # If we have 3 transactions for this order, and all have 'order_income', we shouldn't sum 3 times.
                                # We should typically use the 'max' found logic or only read from one specific type.
                                pass
             
            # Payout is sum of all transactions for this order
            payout_amount = sum(float(t.amount) for t in txs)
            
            # Special logic for Shopee AMS (Affiliate) if not captured
            # Check if any transaction has raw_data with AMS fee
            if platform == 'shopee' and affiliate_cost == 0:
                for tx in txs:
                    raw = tx.raw_data or {}
                    income = raw.get('order_income', {})
                    ams = float(income.get('ams_commission_fee') or 0) + float(income.get('order_ams_commission_fee') or 0)
                    if ams > 0:
                        affiliate_cost = ams
                        # Subtract from payout? Usually payout already deducts it? 
                        # Payout = Sum(amounts). If AMS wasn't a separate negative row, then Payout is inflated?
                        # Wait, 'order_income' fields like 'ams_commission_fee' are informational. 
                        # Actual deduction happens in 'escrow_amount'.
                        # If Shopee didn't generate a specific transaction line for AMS, 
                        # then 'payout_amount' (sum of lines) might be correct (net), 
                        # but 'affiliate_cost' breakdown would be missing.
                        # So we can safely specific affiliate_cost here for display without altering Payout.
                        break
            
            # Payout is sum of all transactions for this order
            payout_amount = sum(float(t.amount) for t in txs)
        else:
            # Fallback to Estimates if no finance data
            payout_amount = (gross_sales + shipping_income) - (gross_sales * 0.12) # Dummy est
            transaction_fee = gross_sales * 0.03
            commission = gross_sales * 0.04
            service_fee = gross_sales * 0.05
        
        # Total Revenue
        total_revenue = gross_sales + shipping_income + platform_discount
        
        # Total Deductions
        total_fees = commission + transaction_fee + service_fee + shipping_cost + affiliate_cost + other_fees
        
        # Net Profit
        # Profit = Revenue - Fees - COGS
        # Note: Payout usually includes shipping income but excludes platform discount (which is subsidized)
        # So Profit = (Payout + Subsidies) - COGS ?? 
        # Simpler: Profit = (Sales + ShipIncome) - Fees - COGS
        net_profit = total_revenue - total_fees - cogs
        
        writer.writerow([
            order_date,
            platform,
            order_id,
            items_str,
            f"{gross_sales:.2f}",
            f"{shipping_income:.2f}",
            f"{platform_discount:.2f}",
            f"{total_revenue:.2f}",
            
            f"{commission:.2f}",
            f"{transaction_fee:.2f}",
            f"{service_fee:.2f}",
            f"{shipping_cost:.2f}",
            f"{affiliate_cost:.2f}",
            f"{total_fees:.2f}",
            
            f"{cogs:.2f}",
            f"{net_profit:.2f}",
            f"{payout_amount:.2f}"
        ])
        
    output.seek(0)
    
    # Add BOM
    bom = '\ufeff'
    content = bom + output.getvalue()
    
    response = StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8"
    )
    
    filename = f"รายงานละเอียด_{start_date}_{end_date}.csv"
    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
    
    return response

