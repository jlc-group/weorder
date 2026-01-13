
import logging
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import OrderHeader, InvoiceProfile
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_invoices():
    db = SessionLocal()
    try:
        logger.info("Starting invoice backfill...")
        
        # 1. Get all Shopee/Lazada orders without InvoiceProfile
        # Using LEFT JOIN to find missing invoices
        sql = """
            SELECT o.id, o.external_order_id, o.channel_code, o.raw_payload, o.customer_name, o.customer_address, o.customer_phone
            FROM order_header o
            LEFT JOIN invoice_profile ip ON o.id = ip.order_id
            WHERE ip.id IS NULL
            AND o.channel_code IN ('shopee', 'lazada')
            AND o.raw_payload IS NOT NULL
        """
        
        result = db.execute(text(sql))
        orders = result.fetchall()
        logger.info(f"Found {len(orders)} candidate orders for backfill")
        
        count = 0
        for row in orders:
            order_id = row[0]
            external_id = row[1]
            channel = row[2]
            payload = row[3]
            customer_name = row[4]
            customer_address = row[5]
            customer_phone = row[6]
            
            invoice_data = None
            platform_data = None
            
            if channel == 'shopee':
                if payload and isinstance(payload, dict):
                    # Check for invoice_data
                    inv = payload.get('invoice_data')
                    if inv:
                        # Validate it's not empty/null "null" string
                        if isinstance(inv, str) and (inv == 'null' or len(inv) < 5):
                            continue
                        if isinstance(inv, dict) and not inv:
                            continue
                            
                        invoice_data = inv
                        platform_data = {
                            "platform": "SHOPEE",
                            "raw_data": inv,
                            "order_sn": external_id
                        }
                        
            elif channel == 'lazada':
                if payload and isinstance(payload, dict):
                    tax_code = payload.get('tax_code')
                    # Filter invalid tax codes
                    if tax_code and tax_code.lower() not in ['lazada', 'shopee', 'tiktok', '', 'null']:
                        invoice_data = {
                            "tax_id": tax_code,
                            "branch": payload.get('branch_number', '00000'),
                            "invoice_name": customer_name,
                            "platform": "lazada"
                        }
                        platform_data = {
                            "platform": "LAZADA",
                            "raw_data": invoice_data,
                            "order_sn": external_id
                        }
            
            if invoice_data:
                try:
                    # Extract info for fields
                    if channel == 'shopee':
                        # Shopee structure: {number, series_number, info: {...}} directly or inside 'info'
                        info = invoice_data.get('info', invoice_data)
                    else:
                        info = invoice_data
                        
                    tax_id = info.get('tax_code') or info.get('tax_id')
                    
                    if not tax_id:
                        continue
                        
                    profile = InvoiceProfile(
                        order_id=order_id,
                        profile_type="COMPANY" if tax_id else "PERSONAL",
                        invoice_name=info.get('name') or info.get('invoice_name') or customer_name,
                        tax_id=tax_id,
                        branch=info.get('branch') or "00000",
                        address_line1=info.get('address') or customer_address,
                        phone=info.get('phone') or customer_phone,
                        email=info.get('email'),
                        status="PENDING",
                        created_source="PLATFORM_SYNC",
                        platform_invoice_data=platform_data,
                        platform_synced_at=datetime.utcnow()
                    )
                    
                    db.add(profile)
                    count += 1
                    
                    if count % 100 == 0:
                        db.commit()
                        logger.info(f"Committed {count} invoice profiles")
                        
                except Exception as e:
                    logger.error(f"Error creating profile for {external_id}: {e}")
                    continue
        
        db.commit()
        logger.info(f"Backfill complete. Created {count} InvoiceRecords.")
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_invoices()
