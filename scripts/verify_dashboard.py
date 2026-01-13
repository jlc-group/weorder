
from app.core import get_db
from app.services import OrderService
from datetime import datetime, date

db = next(get_db())

print("=== Dashboard Stats Verification ===")
# Test "This Month" (Jan 2026 if today is Jan 3)
start_date = "2026-01-01"
end_date = "2026-01-31" 

stats = OrderService.get_dashboard_stats(db, start_date=start_date, end_date=end_date)

print(f"Period: {start_date} to {end_date}")
print(f"Total Orders: {stats['period_orders']}")
print(f"Total Revenue: {stats['period_revenue']}")
print(f"Status Counts: {stats['status_counts']}")
print(f"Platform Breakdown: {stats['platform_breakdown']}")

print("\n=== Real DB Counts Check (SQL) ===")
from sqlalchemy import text
result = db.execute(text(f"""
    SELECT channel_code, COUNT(*), SUM(total_amount)
    FROM order_header 
    WHERE order_datetime >= '2026-01-01' 
    AND status_normalized NOT IN ('CANCELLED', 'RETURNED')
    GROUP BY channel_code
"""))
for row in result.fetchall():
    print(f"Platform: {row[0]}, Count: {row[1]}, Rev: {row[2]}")
