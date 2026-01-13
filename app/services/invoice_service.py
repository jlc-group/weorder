"""
Invoice Service - Tax Invoice Generation
"""
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from app.models import OrderHeader, OrderItem
from app.models.invoice import InvoiceProfile


# Seller Information (Hardcoded)
SELLER_INFO = {
    "name": "บริษัท เจแอลซี กรุ๊ป จำกัด",
    "tax_id": "0105552137425",
    "branch": "สำนักงานใหญ่",
    "address": "62 ซอยนาคนิวาส 6 ถนนนาคนิวาส แขวงลาดพร้าว เขตลาดพร้าว กรุงเทพมหานคร",
    "phone": "",
}


class InvoiceService:
    """Service for generating Tax Invoices"""
    
    @staticmethod
    def generate_invoice_number(order: OrderHeader) -> str:
        """Generate invoice number based on order date"""
        # Format: INV-YYYYMM-ORDERID (last 4 chars)
        order_date = order.order_datetime or datetime.now()
        order_id_suffix = str(order.id)[-4:].upper()
        return f"INV-{order_date.strftime('%Y%m')}-{order_id_suffix}"
    
    @staticmethod
    def get_invoice_data(db: Session, order_id: UUID) -> Optional[dict]:
        """Get all data needed for tax invoice"""
        # Fetch order with items
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            return None
        
        # Fetch invoice profile if exists
        invoice_profile = db.query(InvoiceProfile).filter(
            InvoiceProfile.order_id == order_id
        ).first()
        
        # Determine buyer info (from InvoiceProfile or Order)
        if invoice_profile:
            buyer_info = {
                "name": invoice_profile.invoice_name,
                "tax_id": invoice_profile.tax_id or "-",
                "branch": invoice_profile.branch or "สำนักงานใหญ่",
                "address": ", ".join(filter(None, [
                    invoice_profile.address_line1,
                    invoice_profile.address_line2,
                    invoice_profile.subdistrict,
                    invoice_profile.district,
                    invoice_profile.province,
                    invoice_profile.postal_code
                ])),
                "phone": invoice_profile.phone or "-",
            }
        else:
            # Fallback to order customer info
            buyer_info = {
                "name": order.customer_name or "ลูกค้าทั่วไป",
                "tax_id": "-",
                "branch": "-",
                "address": order.customer_address or "-",
                "phone": order.customer_phone or "-",
            }
        
        # Calculate VAT (assume prices include VAT 7%)
        subtotal_with_vat = float(order.subtotal_amount or 0)
        vat_rate = Decimal("0.07")
        # Price includes VAT, so: price = base + base*0.07 = base * 1.07
        # base = price / 1.07
        base_amount = subtotal_with_vat / 1.07
        vat_amount = subtotal_with_vat - base_amount
        
        # Prepare line items
        items = []
        for idx, item in enumerate(order.items, start=1):
            unit_price = float(item.unit_price or 0)
            quantity = item.quantity or 1
            line_total = float(item.line_total or 0)
            items.append({
                "no": idx,
                "description": item.product_name or item.sku,
                "sku": item.sku,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            })
        
        # Invoice number
        invoice_number = InvoiceService.generate_invoice_number(order)
        
        # Sales Person
        sales_person = order.sales_by or order.channel_code or "-"
        
        # Calculate Baht Text
        baht_text = InvoiceService.numeric_to_thai(order.total_amount or 0)
        
        return {
            "invoice_number": invoice_number,
            "invoice_date": datetime.now().strftime("%d/%m/%Y"),
            "order_id": order.external_order_id,
            "order_date": order.order_datetime.strftime("%d/%m/%Y") if order.order_datetime else "-",
            "channel": order.channel_code,
            "sales_person": sales_person,
            "seller": SELLER_INFO,
            "buyer": buyer_info,
            "items": items,
            "subtotal": round(base_amount, 2),
            "vat_rate": 7,
            "vat_amount": round(vat_amount, 2),
            "shipping_fee": float(order.shipping_fee or 0),
            "discount": float(order.discount_amount or 0),
            "grand_total": float(order.total_amount or 0),
            "grand_total_text": baht_text,
        }

    @staticmethod
    def numeric_to_thai(number_val):
        """
        Convert number to Thai text (BahtText)
        Simple implementation or placeholder
        """
        # Minimal implementation for common cases
        # Or better: Attempt to import bahttext, if fail, fallback
        try:
            from bahttext import bahttext
            return bahttext(number_val)
        except ImportError:
            # Fallback simple text (User might not have lib)
            # return f"({number_val:,.2f} บาท)"
            return InvoiceService._simple_baht_text(number_val)

    @staticmethod
    def _simple_baht_text(number):
        # Implementation of BahtText logic
        try:
            import math
            number = float(number)
            text_num = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
            text_digit = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]
            
            baht = int(number)
            satang = int(round((number - baht) * 100))
            
            if baht == 0 and satang == 0:
                return "ศูนย์บาทถ้วน"
            
            output = ""
            if baht > 0:
                s_baht = str(baht)
                len_baht = len(s_baht)
                for i, digit in enumerate(s_baht):
                    digit = int(digit)
                    pos = len_baht - i - 1
                    if digit != 0:
                        if pos == 0 and digit == 1 and len_baht > 1:
                            output += "เอ็ด"
                        elif pos == 1 and digit == 2:
                            output += "ยี่"
                        elif pos == 1 and digit == 1:
                            pass
                        else:
                            output += text_num[digit]
                        output += text_digit[pos]
                output += "บาท"
            
            if satang > 0:
                s_satang = str(satang)
                len_satang = len(s_satang)
                for i, digit in enumerate(s_satang):
                    digit = int(digit)
                    pos = len_satang - i - 1
                    if digit != 0:
                        if pos == 0 and digit == 1 and len_satang > 1:
                            output += "เอ็ด"
                        elif pos == 1 and digit == 2:
                            output += "ยี่"
                        elif pos == 1 and digit == 1:
                            pass
                        else:
                            output += text_num[digit]
                        output += text_digit[pos]
                output += "สตางค์"
            else:
                output += "ถ้วน"
                
            return output
        except:
            return f"({number:,.2f} บาท)"
