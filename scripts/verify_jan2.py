import sys
import os
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader
from sqlalchemy import func, text

def check_jan2():
    db = SessionLocal()
    # UTC Times for Jan 2 (Assuming +7 Local)
    # Local: 2026-01-02 00:00 - 23:59
    # UTC:   2026-01-01 17:00 - 2026-01-02 16:59
    
    # Actually report uses local date string passed to query, which converts to start/end UTC.
    # Logic in ReportService: 
    # start_date = datetime.strptime(date_str, "%Y-%m-%d") (Local midnight)
    # start_utc = start_date - timedelta(hours=7) (if +7 assumption used or if logic handles it)
    
    # Let's match implicit assumption: Report usually takes dateStr.
    # Let's just query purely on what would show up for "2026-01-02" if requested via API.
    # But for raw DB check, let's look at `shipped_at` in a wide range to be sure.
    
    print("--- Checking Database for 'shipped_at' around Jan 2, 2026 ---")
    
    # We'll use a raw SQL to see exactly what's there
    sql = text("""
        SELECT channel_code, COUNT(*), MIN(shipped_at), MAX(shipped_at)
        FROM order_header
        WHERE shipped_at >= '2026-01-01 17:00:00+00' AND shipped_at < '2026-01-02 17:00:00+00'
        GROUP BY channel_code
    """)
    # Note: 2026-01-02 local is 2026-01-01 17:00 UTC to 2026-01-02 17:00 UTC
    
    results = db.execute(sql).fetchall()
    
    if not results:
        print("✅ Result: 0 Orders found for Jan 2 (Local Time). Clean!")
    else:
        print("⚠️  Orders Found:")
        for r in results:
            print(f"   - {r[0]}: {r[1]} orders (Time range: {r[2]} - {r[3]})")

    print("\n--- Checking for potential ghosts (updated_at on Jan 2 but shipped_at is NULL) ---")
    sql_ghost = text("""
        SELECT channel_code, COUNT(*)
        FROM order_header
        WHERE updated_at >= '2026-01-01 17:00:00+00' AND updated_at < '2026-01-02 17:00:00+00'
        AND shipped_at IS NULL
        AND status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
        GROUP BY channel_code
    """)
    ghosts = db.execute(sql_ghost).fetchall()
    for g in ghosts:
        print(f"   - {g[0]}: {g[1]} orders (Correctly excluded from report)")

    db.close()

if __name__ == "__main__":
    check_jan2()
