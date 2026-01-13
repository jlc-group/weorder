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
    sort: str = Query("date_desc", regex="^(date_asc|date_desc|amount_asc|amount_desc)$"),
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
    
    # Get calculated profit record
    from app.models.finance import order_profit
    # Actually, order_profit might be a table/model not imported?
    # I see it in psql \dt. Let's check imports.
    # It was 'from app.models.finance import MarketplaceTransaction' above.
    # Let me check if order_profit is in app.models.order or finance.
    
    # Based on previous psql \d, it references company and order_header.
    # I'll try to find the model definition.
    
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
