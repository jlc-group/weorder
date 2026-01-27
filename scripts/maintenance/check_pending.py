"""Check all PAID orders (not just today)"""
import psycopg2
from datetime import datetime, date
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host="192.168.0.41",
    database="weorder_db",
    user="weorder_user",
    password="sZ3vlr2tzjz5x#T8",
    port=5432
)
cur = conn.cursor()

print("=== All TikTok Orders Pending Ship ===\n")

# 1. All PAID (pending ship) regardless of date
print("1. All PAID orders (any date):")
cur.execute("""
    SELECT COUNT(*) FROM order_header
    WHERE channel_code = 'tiktok'
      AND status_normalized = 'PAID'
""")
paid_all = cur.fetchone()[0]
print(f"   Total PAID: {paid_all}")

# 2. READY_TO_SHIP
cur.execute("""
    SELECT COUNT(*) FROM order_header
    WHERE channel_code = 'tiktok'
      AND status_normalized = 'READY_TO_SHIP'
""")
rts = cur.fetchone()[0]
print(f"   READY_TO_SHIP: {rts}")

# 3. Total pending = PAID + READY_TO_SHIP
print(f"\n   Total pending (PAID + RTS): {paid_all + rts}")

# 4. Breakdown by order date
print("\n2. PAID orders by order date:")
cur.execute("""
    SELECT DATE(order_datetime AT TIME ZONE 'Asia/Bangkok'), COUNT(*)
    FROM order_header
    WHERE channel_code = 'tiktok'
      AND status_normalized = 'PAID'
    GROUP BY DATE(order_datetime AT TIME ZONE 'Asia/Bangkok')
    ORDER BY DATE(order_datetime AT TIME ZONE 'Asia/Bangkok') DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]}")

# 5. All pending statuses
print("\n3. All non-shipped/cancelled orders:")
cur.execute("""
    SELECT status_normalized, COUNT(*) FROM order_header
    WHERE channel_code = 'tiktok'
      AND status_normalized NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED', 'COMPLETED')
    GROUP BY status_normalized
""")
total_pending = 0
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]}")
    total_pending += row[1]
print(f"   TOTAL PENDING: {total_pending}")

cur.close()
conn.close()
