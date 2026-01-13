#!/usr/bin/env python3
"""
MANUAL Force Sync for TikTok Jan 8-10.
DIRECTLY inserts orders if they are missing, bypassing sync service checks.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.core import SessionLocal
from app.models.integration import PlatformConfig
from app.models.order import OrderHeader, OrderItem
from app.models.master import Company
from app.services import integration_service
from sqlalchemy import text

TZ = ZoneInfo("Asia/Bangkok")

def insert_order(db, normalized, company_id):
    """Manually insert an order"""
    # Construct full address
    address_parts = [
        normalized.shipping_address,
        normalized.shipping_district,
        normalized.shipping_city,
        normalized.shipping_province,
        normalized.shipping_postal_code,
        normalized.shipping_country
    ]
    full_address = " ".join([p for p in address_parts if p])

    # Extract extra fields if possible (simplified from sync_service)
    raw = normalized.raw_payload
    
    order = OrderHeader(
        company_id=company_id,
        channel_code=normalized.platform,
        external_order_id=normalized.platform_order_id,
        
        customer_name=normalized.customer_name,
        customer_phone=normalized.customer_phone,
        customer_address=full_address,
        
        status_raw=normalized.order_status,
        status_normalized=normalized.status_normalized,
        
        subtotal_amount=normalized.subtotal,
        shipping_fee=normalized.shipping_fee,
        discount_amount=normalized.discount_amount,
        total_amount=normalized.total_amount,
        
        payment_method=normalized.payment_method,
        shipping_method=normalized.shipping_method,
        tracking_number=normalized.tracking_number,
        courier_code=normalized.courier,
        
        shipped_at=normalized.shipped_at,
        order_datetime=normalized.order_created_at or datetime.utcnow(),
        
        raw_payload=normalized.raw_payload,
        
        # Basic extra fields if present in raw
        is_cod=raw.get('is_cod', False) if raw else False,
    )
    
    db.add(order)
    db.flush()
    
    for item_data in normalized.items:
        item = OrderItem(
            order_id=order.id,
            sku=item_data.get("sku", ""),
            product_name=item_data.get("product_name", ""),
            quantity=item_data.get("quantity", 1),
            unit_price=item_data.get("unit_price", 0),
            line_total=item_data.get("total_price", 0),
            line_discount=item_data.get("discount_amount", 0),
            original_price=item_data.get("original_price", 0),
            platform_discount=item_data.get("platform_discount", 0),
            seller_discount=item_data.get("seller_discount", 0),
        )
        db.add(item)
    
    return True

async def process_day(db, client, company_id, day):
    """Process a single day"""
    start_utc = datetime(2026, 1, day, 0, 0, 0, tzinfo=TZ).astimezone(timezone.utc)
    end_utc = datetime(2026, 1, day, 23, 59, 59, tzinfo=TZ).astimezone(timezone.utc)
    
    print(f"Syncing Jan {day} (UTC: {start_utc} - {end_utc})...")
    
    total_fetched = 0
    total_added = 0
    total_skipped = 0
    
    cursor = None
    has_more = True
    
    while has_more:
        try:
            result = await client.get_orders(
                time_from=start_utc,
                time_to=end_utc,
                cursor=cursor,
                page_size=100
            )
            orders = result.get("orders", [])
            total_fetched += len(orders)
            
            for raw_order in orders:
                # Normalize using client
                try:
                    normalized = client.normalize_order(raw_order)
                    order_id = normalized.platform_order_id
                    
                    # Direct DB check
                    existing = db.query(OrderHeader).filter(
                        OrderHeader.external_order_id == order_id,
                        OrderHeader.channel_code == "tiktok"
                    ).first()
                    
                    if not existing:
                        insert_order(db, normalized, company_id)
                        total_added += 1
                    else:
                        # Force update order_datetime if different
                        new_dt = normalized.order_created_at or datetime.utcnow()
                        # Simple comparison (aware/naive handling needed)
                        if existing.order_datetime != new_dt:
                            existing.order_datetime = new_dt
                            # Also update status just in case
                            existing.status_raw = normalized.order_status
                            existing.status_normalized = normalized.status_normalized
                            total_fetched += 1 # Count as update interaction
                        total_skipped += 1 # Still technically skipped insert
                    
                    if (total_added + total_skipped) % 50 == 0:
                        db.commit()
                        print(f"  Processed {total_added + total_skipped} orders...")
                        
                except Exception as e:
                    print(f"  Error processing order: {e}")
            
            db.commit() # Commit batch
            
            cursor = result.get("next_cursor")
            has_more = result.get("has_more", False) and cursor
            
        except Exception as e:
            print(f"  Error fetching page: {e}")
            break
            
    print(f"Jan {day}: Fetched={total_fetched}, Added={total_added}, Skipped={total_skipped}")

async def main():
    db = SessionLocal()
    
    # Get Company ID
    company = db.query(Company).first()
    if not company:
        print("No company found")
        return
    company_id = company.id
    
    # Get TikTok config
    config = db.query(PlatformConfig).filter(
        PlatformConfig.platform == "tiktok",
        PlatformConfig.is_active == True
    ).first()
    
    if not config:
        print("No TikTok config")
        return

    client = integration_service.get_client_for_config(config)
    
    # Days to sync: 9 only (final check)
    for day in [9]:
        await process_day(db, client, company_id, day)
    
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
