
import sys
import os
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
try:
    from app.core import settings
    from app.services.report_service import ReportService
except ImportError:
    # Fallback if app.core structure is complex, but usually settings is enough
    # We really just need the DB connection
    pass

# Direct DB connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def check_trend():
    print(f"{'Date':<12} | {'Shopee':<8} | {'Lazada':<8} | {'TikTok':<8} | {'Total':<8}")
    print("-" * 50)
    
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 12)
    
    current = start_date
    while current <= end_date:
        # We can't easily use ReportService here because of dependency injection complexity in script
        # So we replicate the Noon-to-Noon logic simply
        
        # Window: (Day-1 12:00) to (Day 12:00)
        # Wait, ReportService logic: 
        # get_daily_outbound_stats(date=current) -> 
        # start = (current - 1_day) at cutoff_hour
        # end = current at cutoff_hour
        
        day_start = datetime.combine(current - timedelta(days=1), datetime.min.time()).replace(hour=12)
        day_end = datetime.combine(current, datetime.min.time()).replace(hour=12)
        
        # Query rts_time if available, else fallback? 
        # ReportService uses rts_time primarily now.
        
        q = """
            SELECT channel_code, count(*) 
            FROM order_header 
            WHERE status_normalized NOT IN ('CANCELLED', 'RETURNED')
            AND (
                (rts_time >= :start AND rts_time < :end)
                OR
                (rts_time IS NULL AND order_datetime >= :start AND order_datetime < :end)
            )
            GROUP BY channel_code
        """
        
        # Note: We are mixing rts_time (which is UTC in DB) with Naive 'day_start'
        # But wait, python datetime without tzinfo is naive. 
        # Database timestamps are... typically stored as UTC or Naive depending on setup.
        # In previous steps we saw Naive comparisons working for 'rts_time' (stored as timestamp w/o tz in some tests? No, typically with TZ).
        # Let's trust previous findings: Naive UTC strings work well against DB.
        
        # Shift to UTC for query if DB expects UTC
        # Thai 12:00 = UTC 05:00
        utc_start = day_start - timedelta(hours=7)
        utc_end = day_end - timedelta(hours=7)
        
        res = db.execute(text(q), {"start": utc_start, "end": utc_end}).fetchall()
        
        counts = {'shopee': 0, 'lazada': 0, 'tiktok': 0}
        for row in res:
            ch = row[0]
            cnt = row[1]
            if ch in counts:
                counts[ch] = cnt
                
        total = sum(counts.values())
        print(f"{current}   | {counts['shopee']:<8} | {counts['lazada']:<8} | {counts['tiktok']:<8} | {total:<8}")
        
        current += timedelta(days=1)

if __name__ == "__main__":
    check_trend()
    db.close()
