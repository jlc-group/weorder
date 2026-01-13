
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
from app.services import integration_service
from app.models import OrderHeader, InvoiceProfile
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def sync_shopee_invoices():
    db = next(get_db())
    try:
        # 1. Get active Shopee config
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs:
            logger.error("No active Shopee configuration found")
            return
        
        config = configs[0]
        client = integration_service.get_client_for_config(config)
        logger.info(f"Using Shopee Account: {config.shop_name} (ID: {config.shop_id})")
        
        # 2. Find Shopee orders that DON'T have an InvoiceProfile yet
        #    Targeting orders from 2025 onwards
        logger.info("Finding Shopee orders needing invoice sync...")
        
        sql = """
            SELECT o.id, o.external_order_id, o.order_datetime
            FROM order_header o
            LEFT JOIN invoice_profile ip ON o.id = ip.order_id
            WHERE o.channel_code = 'shopee'
            AND o.order_datetime >= '2025-12-01'
            AND ip.id IS NULL
            ORDER BY o.order_datetime DESC
        """
        
        result = db.execute(text(sql))
        orders = result.fetchall()
        total_orders = len(orders)
        logger.info(f"Found {total_orders} orders to check.")
        
        # 3. Process orders
        processed = 0
        found_invoices = 0
        
        for row in orders:
            order_id = row[0]
            order_sn = row[1]
            
            processed += 1
            if processed % 100 == 0:
                 logger.info(f"Progress: {processed}/{total_orders} orders processed.")
                
            if processed % 10 == 0:
                print(f"Processing {processed}/{total_orders} : {order_sn}")
            
            try:
                # Call Shopee API (Use get_order_detail)
                # Get invoice info from order detail (more reliable)
                logger.info(f"Fetching details for order {order_sn}...")
                order_detail = await client.get_order_detail(order_sn)
                
                if not order_detail:
                    logger.warning(f"No details returned for order {order_sn} (order_detail is empty)")
                    continue
                    
                # Invoice Data Strategy:
                # 1. Try to get official 'invoice_data' (Tax Invoice)
                # 2. If missing, fallback to 'recipient_address' (Personal Invoice)
                
                invoice_data = order_detail.get("invoice_data")
                recipient = order_detail.get("recipient_address", {})
                
                profile_data = {}
                
                if invoice_data:
                    # Case A: Official Tax Invoice Request
                    profile_data = {
                        "type": "COMPANY" if invoice_data.get("tax_code") else "PERSONAL",
                        "name": invoice_data.get("name") or invoice_data.get("invoice_name"),
                        "tax_id": invoice_data.get("tax_code") or "",
                        "branch": invoice_data.get("branch") or "00000",
                        "address": invoice_data.get("address"),
                        "phone": invoice_data.get("phone"),
                        "email": invoice_data.get("email"),
                        "raw": invoice_data,
                        "source_type": "OFFICIAL_REQUEST"
                    }
                    logger.info(f"📄 Found Official Invoice Request for {order_sn}")
                else:
                    # Case B: No Invoice Data - Skip
                    # logger.info(f"No Official Invoice Request for {order_sn}")
                    continue

                # Create InvoiceProfile
                # Double check if profile exists (race condition check)
                existing = db.query(InvoiceProfile).filter(InvoiceProfile.order_id == order_id).first()
                if existing:
                    continue
                    
                profile = InvoiceProfile(
                    order_id=order_id,
                    profile_type=profile_data["type"],
                    invoice_name=profile_data["name"] or "-",
                    tax_id=profile_data["tax_id"],
                    branch=profile_data["branch"],
                    address_line1=profile_data["address"] or "-",
                    phone=profile_data["phone"] or "",
                    email=profile_data["email"],
                    status="PENDING",
                    created_source="PLATFORM_API",
                    platform_invoice_data={
                        "platform": "SHOPEE",
                        "source": "API",
                        "source_type": profile_data["source_type"],
                        "raw_data": profile_data["raw"],
                        "synced_at": datetime.utcnow().isoformat()
                    },
                    platform_synced_at=datetime.utcnow()
                )
                
                db.add(profile)
                db.commit()
                found_invoices += 1
                if found_invoices % 10 == 0:
                    logger.info(f"✅ Created {found_invoices} profiles so far...")
                
                # Rate limit protection (Shopee has limits)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error processing {order_sn}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue to next order
                continue
                
        logger.info(f"\nSync Complete! Processed: {processed}, New Invoices Found: {found_invoices}")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_shopee_invoices())
