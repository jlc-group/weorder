import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine
from app.core import SessionLocal
from app.models import OrderHeader, OrderItem
from app.models.integration import PlatformConfig
from app.integrations.lazada import LazadaClient

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB
DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

async def backfill_lazada():
    db = SessionLocal()
    try:
        # Get Config
        config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
        if not config:
            logger.error("No active Lazada config")
            return

        client = LazadaClient(
            app_key=config.app_key,
            app_secret=config.app_secret,
            shop_id=config.shop_id,
            access_token=config.access_token,
            refresh_token=config.refresh_token
        )

        # 1. Find target orders
        logger.info("Fetching Lazada orders to backfill...")
        
        # Target: Lazada orders updated on Jan 2 with missing items or NULL shipped_at
        # Actually, let's just target the 425 identified by date range
        orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'lazada',
            OrderHeader.updated_at >= '2026-01-02 00:00:00',
            OrderHeader.updated_at < '2026-01-03 00:00:00',
            OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED', 'RETURNED'])
        ).all()
        
        logger.info(f"Found {len(orders)} Lazada orders to fix.")
        
        updated_count = 0
        
        for order in orders:
            try:
                # 1. Update Date
                detail = await client.get_order_detail(order.external_order_id)
                api_updated_at_str = detail.get("updated_at")
                
                if api_updated_at_str:
                    # Parse "2025-12-31 10:26:46 +0700"
                    # Lazada format is tricky. Using strptime or simplified parsing
                    # Example: 2025-12-31 10:26:46 +0700
                    try:
                         # Remove time zone for simplified parsing/handling or use generic parser
                         # Actually base.py has fromisoformat, but this format space +0700 might be weird
                         # Let's try simple split
                         dt_part = api_updated_at_str.split(" +")[0]
                         new_shipped_at = datetime.strptime(dt_part, "%Y-%m-%d %H:%M:%S")
                         # Assume local -> UTC conversion if needed? Or just store naive if DB is naive
                         # DB is UTC. Lazada is likely +0700.
                         # Subtract 7 hours to get UTC
                         from datetime import timedelta
                         new_shipped_at_utc = new_shipped_at - timedelta(hours=7)
                         
                         order.shipped_at = new_shipped_at_utc
                         # Also fix updated_at to match reality if we want to move it out of report
                         # But let's stick to shipped_at for report filter
                    except Exception as e:
                        logger.error(f"Date parse error {api_updated_at_str}: {e}")
                
                # 2. Sync Items
                raw_items = await client.get_order_items(order.external_order_id)
                if raw_items:
                    # Check if items exist
                    existing_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).count()
                    if existing_items == 0:
                        for item in raw_items:
                            db_item = OrderItem(
                                order_id=order.id,
                                # platform_item_id not in model
                                sku=item.get("sku"),
                                product_name=item.get("name"),
                                quantity=1, # Lazada is 1 item per row usually
                                unit_price=float(item.get("paid_price", 0)),
                                line_total=float(item.get("paid_price", 0)),
                                # variation=item.get("variation") # variation not in model visible in file lines 93-124
                            )
                            db.add(db_item)
                
                db.commit()
                updated_count += 1
                if updated_count % 10 == 0:
                    logger.info(f"Processed {updated_count}/{len(orders)}")
                
                # Rate limit
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error processing {order.external_order_id}: {e}")
                db.rollback()
        
        logger.info("Lazada Backfill Complete!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(backfill_lazada())
