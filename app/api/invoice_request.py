"""
Invoice Request API - Customer-facing endpoints for tax invoice requests
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.core import get_db
from app.models import OrderHeader
from app.models.invoice import InvoiceProfile


invoice_request_router = APIRouter(prefix="/invoice-request", tags=["Invoice Request"])


class InvoiceRequestCreate(BaseModel):
    """Request body for creating an invoice request"""
    order_id: str = Field(..., description="Order ID (external or internal UUID)")
    profile_type: str = Field("PERSONAL", description="PERSONAL or COMPANY")
    invoice_name: str = Field(..., description="Name for the invoice")
    tax_id: str = Field(..., description="Tax ID (13 digits)")
    branch: str = Field("00000", description="Branch code (00000 for HQ)")
    address_line1: str = Field(..., description="Address line 1")
    address_line2: Optional[str] = None
    subdistrict: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class InvoiceRequestStatus(BaseModel):
    """Response for invoice request status"""
    order_id: str
    external_order_id: Optional[str]
    status: str
    invoice_name: str
    tax_id: str
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    can_download: bool
    download_url: Optional[str]
    message: str


def get_order_by_any_id(db: Session, order_id: str):
    """Find order by UUID or external ID"""
    # Try UUID first
    try:
        order = db.query(OrderHeader).filter(OrderHeader.id == UUID(order_id)).first()
        if order:
            return order
    except:
        pass
    
    # Try external order ID
    order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
    return order


@invoice_request_router.post("")
def create_invoice_request(data: InvoiceRequestCreate, db: Session = Depends(get_db)):
    """
    Customer submits a tax invoice request.
    
    Rules:
    - Order must be in DELIVERED status
    - Request must be within 3 days of delivery
    - Only one request per order
    """
    # Find order
    order = get_order_by_any_id(db, data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="ไม่พบหมายเลขคำสั่งซื้อนี้ในระบบ")
    
    # Check order status
    if order.status_normalized != "DELIVERED":
        if order.status_normalized in ["NEW", "PAID", "PACKING", "SHIPPED"]:
            raise HTTPException(
                status_code=400, 
                detail=f"ยังไม่สามารถขอใบกำกับภาษีได้ เนื่องจากสินค้ายังไม่ถึงมือลูกค้า (สถานะปัจจุบัน: {order.status_normalized})"
            )
        elif order.status_normalized in ["CANCELLED", "RETURNED"]:
            raise HTTPException(
                status_code=400, 
                detail="ไม่สามารถขอใบกำกับภาษีได้ เนื่องจากคำสั่งซื้อถูกยกเลิกหรือคืนสินค้าแล้ว"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"ไม่สามารถขอใบกำกับภาษีได้ (สถานะ: {order.status_normalized})"
            )
    
    # Check 3-day deadline (from order_datetime or updated_at as proxy for delivery time)
    # In production, you'd want a dedicated "delivered_at" field
    delivery_time = order.updated_at or order.order_datetime
    if delivery_time:
        deadline = delivery_time + timedelta(days=30)
        if datetime.now(delivery_time.tzinfo if hasattr(delivery_time, 'tzinfo') and delivery_time.tzinfo else None) > deadline:
            raise HTTPException(
                status_code=400, 
                detail="เกินระยะเวลาที่กำหนด (สามารถขอใบกำกับภาษีได้ภายใน 30 วันหลังรับสินค้า)"
            )
    
    # Check if already requested
    existing = db.query(InvoiceProfile).filter(InvoiceProfile.order_id == order.id).first()
    if existing:
        # Return existing status instead of error
        return {
            "success": True,
            "message": "คำขอใบกำกับภาษีของคุณอยู่ในระบบแล้ว",
            "status": existing.status,
            "invoice_number": existing.invoice_number,
            "request_id": str(existing.id)
        }
    
    # Validate tax ID (13 digits for Thailand)
    tax_id_clean = data.tax_id.replace("-", "").replace(" ", "")
    if len(tax_id_clean) != 13 or not tax_id_clean.isdigit():
        raise HTTPException(
            status_code=400, 
            detail="เลขประจำตัวผู้เสียภาษีไม่ถูกต้อง (ต้องเป็นตัวเลข 13 หลัก)"
        )
    
    # Create invoice profile
    profile = InvoiceProfile(
        order_id=order.id,
        profile_type=data.profile_type,
        invoice_name=data.invoice_name,
        tax_id=tax_id_clean,
        branch=data.branch,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        subdistrict=data.subdistrict,
        district=data.district,
        province=data.province,
        postal_code=data.postal_code,
        phone=data.phone,
        email=data.email,
        status="PENDING",
        created_source="CUSTOMER_PORTAL"
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "message": "ส่งคำขอใบกำกับภาษีเรียบร้อยแล้ว กรุณารอ 1-3 วันทำการ",
        "status": "PENDING",
        "request_id": str(profile.id)
    }


@invoice_request_router.get("/check/{order_id}")
def check_invoice_request(order_id: str, db: Session = Depends(get_db)):
    """
    Check status of an invoice request by order ID.
    Also used to download issued invoice.
    """
    # Find order
    order = get_order_by_any_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="ไม่พบหมายเลขคำสั่งซื้อนี้ในระบบ")
    
    # Check for invoice profile
    profile = db.query(InvoiceProfile).filter(InvoiceProfile.order_id == order.id).first()
    
    if not profile:
        # No request yet - check if eligible
        can_request = order.status_normalized == "DELIVERED"
        
        # Check 3-day deadline
        deadline_passed = False
        delivery_time = order.updated_at or order.order_datetime
        if delivery_time:
            deadline = delivery_time + timedelta(days=30)
            if datetime.now(delivery_time.tzinfo if hasattr(delivery_time, 'tzinfo') and delivery_time.tzinfo else None) > deadline:
                deadline_passed = True
                can_request = False
        
        return {
            "order_id": str(order.id),
            "external_order_id": order.external_order_id,
            "has_request": False,
            "can_request": can_request,
            "order_status": order.status_normalized,
            "deadline_passed": deadline_passed,
            "message": "ยังไม่มีคำขอใบกำกับภาษี" + (" (เกินระยะเวลา 30 วัน)" if deadline_passed else "")
        }
    
    # Has request
    can_download = profile.status == "ISSUED" and profile.invoice_pdf_path
    
    return {
        "order_id": str(order.id),
        "external_order_id": order.external_order_id,
        "has_request": True,
        "status": profile.status,
        "invoice_name": profile.invoice_name,
        "tax_id": profile.tax_id,
        "invoice_number": profile.invoice_number,
        "invoice_date": profile.invoice_date.strftime("%d/%m/%Y") if profile.invoice_date else None,
        "can_download": can_download,
        "download_url": f"/api/invoice-request/download/{order_id}" if can_download else None,
        "rejected_reason": profile.rejected_reason if profile.status == "REJECTED" else None,
        "message": {
            "PENDING": "คำขอของคุณอยู่ระหว่างดำเนินการ กรุณารอ 1-3 วันทำการ",
            "ISSUED": "ใบกำกับภาษีพร้อมดาวน์โหลดแล้ว",
            "REJECTED": f"คำขอถูกปฏิเสธ: {profile.rejected_reason or 'ไม่ระบุเหตุผล'}"
        }.get(profile.status, "")
    }


@invoice_request_router.get("/download/{order_id}")
def download_invoice(order_id: str, db: Session = Depends(get_db)):
    """
    Download the issued tax invoice PDF.
    """
    from fastapi.responses import HTMLResponse
    from jinja2 import Environment, FileSystemLoader
    from app.services.invoice_service import InvoiceService
    import os
    
    # Find order
    order = get_order_by_any_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="ไม่พบหมายเลขคำสั่งซื้อนี้ในระบบ")
    
    # Check for invoice profile
    profile = db.query(InvoiceProfile).filter(InvoiceProfile.order_id == order.id).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="ไม่พบคำขอใบกำกับภาษี")
    
    if profile.status != "ISSUED":
        raise HTTPException(status_code=400, detail="ใบกำกับภาษียังไม่ได้ออก")
    
    # Generate invoice HTML (same as original tax-invoice endpoint but with InvoiceProfile data)
    invoice_data = InvoiceService.get_invoice_data(db, order.id)
    if not invoice_data:
        raise HTTPException(status_code=500, detail="ไม่สามารถสร้างใบกำกับภาษีได้")
    
    # Override with InvoiceProfile data
    invoice_data["invoice_number"] = profile.invoice_number
    invoice_data["invoice_date"] = profile.invoice_date.strftime("%d/%m/%Y") if profile.invoice_date else datetime.now().strftime("%d/%m/%Y")
    
    # Render template
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("tax_invoice.html")
    
    html = template.render(**invoice_data)
    
    return HTMLResponse(content=html)

@invoice_request_router.get("/lookup")
def lookup_invoice_profile(
    phone: Optional[str] = None, 
    tax_id: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    Lookup latest invoice profile by Tax ID or Phone.
    Used for Autofill.
    """
    if not phone and not tax_id:
        raise HTTPException(status_code=400, detail="Must provide phone or tax_id")
    
    query = db.query(InvoiceProfile).order_by(InvoiceProfile.created_at.desc())
    
    if tax_id:
        # Clean Tax ID
        clean_tax = tax_id.replace("-", "").replace(" ", "")
        query = query.filter(InvoiceProfile.tax_id == clean_tax)
    elif phone:
        # Simple phone matching (exact for now)
        # Ideally should normalize phone
        query = query.filter(InvoiceProfile.phone == phone)
        
    profile = query.first()
    
    if not profile:
        return {"found": False}
        
    return {
        "found": True,
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
        "email": profile.email
    }
