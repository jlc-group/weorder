
import asyncio
import logging
import sys
import os
import time
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
from app.services import integration_service
from app.models import OrderHeader, InvoiceProfile
from sqlalchemy import text
from app.integrations.shopee import ShopeeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# CONFIGURATION
CONCURRENCY_LIMIT = 20  # Number of concurrent requests
BATCH_COMMIT_SIZE = 100 # Commit to DB every N records

async def fetch_invoice_data(
    client: ShopeeClient, 
    order_id: str, 
    order_sn: str, 
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Fetch invoice data for a single order with semaphore limit"""
    async with semaphore:
        try:
            # Add small random delay to prevent thundering herd
            # await asyncio.sleep(0.01) 
            return {
                "order_id": order_id,
                "order_sn": order_sn,
                "data": await client.get_buyer_invoice_info(order_sn),
                "success": True
            }
        except Exception as e:
            # logger.error(f"Failed to fetch {order_sn}: {e}")
            return {
                "order_id": order_id,
                "order_sn": order_sn,
                "error": str(e),
                "success": False
            }

async def sync_shopee_invoices_batch():
    db = next(get_db())
    start_time = time.time()
    
    try:
        # 1. Setup Client
        configs = integration_service.get_platform_configs(db, platform="shopee", is_active=True)
        if not configs:
            logger.error("❌ No active Shopee configuration found")
            return
        
        config = configs[0]
        client = integration_service.get_client_for_config(config)
        logger.info(f"🚀 Starting High-Performance Sync for: {config.shop_name} (ID: {config.shop_id})")
        
        # 2. Fetch Candidates
        logger.info("📊 Fetching candidate orders from Database...")
        sql = """
            SELECT o.id, o.external_order_id
            FROM order_header o
            LEFT JOIN invoice_profile ip ON o.id = ip.order_id
            WHERE o.channel_code = 'shopee'
            AND o.order_datetime >= '2025-01-01'
            AND ip.id IS NULL
            ORDER BY o.order_datetime DESC
        """
        result = db.execute(text(sql))
        orders = result.fetchall()
        total_orders = len(orders)
        logger.info(f"📋 Found {total_orders} orders to process")
        
        if total_orders == 0:
            return

        # 3. Process in chunks
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        processed_count = 0
        found_count = 0
        error_count = 0
        
        # Generator for chunks
        def chunked(iterable, n):
            for i in range(0, len(iterable), n):
                yield iterable[i:i + n]

        # Process batches
        chunk_size = 50 # Create 50 tasks at a time
        
        for chunk in chunked(orders, chunk_size):
            tasks = []
            for row in chunk:
                tasks.append(fetch_invoice_data(client, row[0], row[1], semaphore))
            
            # Wait for this batch
            results = await asyncio.gather(*tasks)
            
            # Process results
            new_profiles = []
            
            for res in results:
                processed_count += 1
                
                if not res["success"]:
                    error_count += 1
                    continue
                
                invoice_info = res.get("data")
                if invoice_info and invoice_info.get("info") and invoice_info.get("info", {}).get("tax_code"):
                    info = invoice_info.get("info")
                    
                    profile = InvoiceProfile(
                        order_id=res["order_id"],
                        profile_type="COMPANY" if info.get("tax_code") else "PERSONAL",
                        invoice_name=info.get("name") or info.get("invoice_name") or "-",
                        tax_id=info.get("tax_code") or "",
                        branch=info.get("branch") or "00000",
                        address_line1=info.get("address") or "-",
                        phone=info.get("phone") or "",
                        email=info.get("email"),
                        status="PENDING",
                        created_source="PLATFORM_API",
                        platform_invoice_data={
                            "platform": "SHOPEE",
                            "source": "API",
                            "raw_data": invoice_info,
                            "synced_at": datetime.utcnow().isoformat()
                        },
                        platform_synced_at=datetime.utcnow()
                    )
                    new_profiles.append(profile)
            
            # Bulk Insert
            if new_profiles:
                db.add_all(new_profiles)
                db.commit()
                found_count += len(new_profiles)
            
            # Progress Report
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            eta = (total_orders - processed_count) / rate if rate > 0 else 0
            
            # Clear line and print progress
            sys.stdout.write(f"\r🚀 Progress: {processed_count}/{total_orders} | Found: {found_count} | Errors: {error_count} | Rate: {rate:.1f}/s | ETA: {eta/60:.1f} min")
            sys.stdout.flush()

        logger.info(f"\n\n✅ Sync Complete in {time.time() - start_time:.1f}s")
        logger.info(f"   Total Processed: {processed_count}")
        logger.info(f"   Invoices Found: {found_count}")
        logger.info(f"   Errors: {error_count}")

    except Exception as e:
        logger.error(f"\n❌ Fatal Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sync_shopee_invoices_batch())
