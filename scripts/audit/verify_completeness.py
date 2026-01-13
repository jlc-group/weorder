
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from app.core import SessionLocal
from app.models import OrderHeader
from app.models.integration import PlatformConfig
from app.integrations.tiktok import TikTokClient

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audit")

async def get_client(db, platform):
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == platform, PlatformConfig.is_active == True).first()
    if not config:
        return None
        
    client = TikTokClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        shop_id=config.shop_id,
        access_token=config.access_token,
        refresh_token=config.refresh_token
    )
    return client

async def check_platform(db, platform="tiktok"):
    logger.info(f"--- Auditing {platform} ---")
    client = await get_client(db, platform)
    if not client:
        return

    # Check Total Count 2025
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    # 1. API Count
    # We use page_size=1 just to get 'total'
    # Note: TikTok search API 'total' might be capped or fuzzy for huge ranges, 
    # but strictly it returns total_count.
    resp = await client.get_orders(time_from=start_date, time_to=end_date, page_size=1)
    api_total = resp.get("total", -1)
    
    logger.info(f"API Reported Total (2025-Now): {api_total}")
    
    # 2. DB Count
    # Query: count of orders created >= 2025-01-01
    db_count = db.query(OrderHeader).filter(
        OrderHeader.channel_code == platform,
        OrderHeader.order_datetime >= start_date.replace(tzinfo=None) # Local DB is naive usually or matches driver
    ).count()
    
    logger.info(f"DB Reported Total  (2025-Now): {db_count}")
    
    diff = api_total - db_count
    match_icon = "✅" if diff == 0 else "❌"
    logger.info(f"Result: {match_icon} Diff: {diff}")
    
    # 3. Anomaly Scan
    logger.info("Scanning for anomalies...")
    
    # 3.1 1970 Dates
    bad_dates = db.query(OrderHeader).filter(
        OrderHeader.channel_code == platform,
        OrderHeader.shipped_at < '2000-01-01',
        OrderHeader.status_normalized.in_(['SHIPPED', 'DELIVERED'])
    ).count()
    
    date_icon = "✅" if bad_dates == 0 else "❌"
    logger.info(f"Invalid Dates (<2000): {bad_dates} {date_icon}")
    
    # 3.2 Monthly Breakdown
    # Fetch API Breakdown? Hard without many requests. 
    # For now, just output DB breakdown for user review.
    rows = db.execute(text(f"""
        SELECT to_char(order_datetime, 'YYYY-MM') as m, count(*) 
        FROM order_header 
        WHERE channel_code = '{platform}' 
        AND order_datetime >= '2025-01-01' 
        GROUP BY 1 ORDER BY 1
    """)).fetchall()
    
    print("\nMonthly Breakdown (DB):")
    for r in rows:
        print(f"{r[0]}: {r[1]}")
        
    return {
        "api_total": api_total,
        "db_total": db_count,
        "bad_dates": bad_dates
    }

async def main():
    db = SessionLocal()
    try:
        await check_platform(db, "tiktok")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
