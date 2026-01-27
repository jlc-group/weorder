"""Verify Daily Outbound data for Jan 5, 2026"""
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

target_date = date(2026, 1, 5)

print(f"=== Verifying Daily Outbound for {target_date} ===\n")

# 1. Check orders by collection_time
print("1. Orders by collection_time:")
cur.execute("""
    SELECT channel_code, COUNT(*), SUM(total_amount)
    FROM order_header
    WHERE DATE(collection_time AT TIME ZONE 'Asia/Bangkok') = %s
      AND status_normalized NOT IN ('CANCELLED', 'RETURNED')
    GROUP BY channel_code
""", (target_date,))
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]} orders, total ฿{row[2]:,.0f}")

# 2. Check orders by shipped_at (fallback)
print("\n2. Orders by shipped_at (where collection_time is null):")
cur.execute("""
    SELECT channel_code, COUNT(*)
    FROM order_header
    WHERE collection_time IS NULL
      AND DATE(shipped_at AT TIME ZONE 'Asia/Bangkok') = %s
      AND status_normalized NOT IN ('CANCELLED', 'RETURNED')
    GROUP BY channel_code
""", (target_date,))
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]} orders")

# 3. Total items on that day
print("\n3. Total items (from order_item):")
cur.execute("""
    SELECT oh.channel_code, SUM(oi.quantity)
    FROM order_item oi
    JOIN order_header oh ON oi.order_id = oh.id
    WHERE DATE(oh.collection_time AT TIME ZONE 'Asia/Bangkok') = %s
      AND oh.status_normalized NOT IN ('CANCELLED', 'RETURNED')
    GROUP BY oh.channel_code
""", (target_date,))
for row in cur.fetchall():
    print(f"   {row[0]}: {int(row[1])} items")

# 4. Check label print log for that date
print("\n4. Label Print Log (packed count):")
cur.execute("""
    SELECT COUNT(*) FROM label_print_log
    WHERE DATE(printed_at AT TIME ZONE 'Asia/Bangkok') = %s
""", (target_date,))
label_count = cur.fetchone()[0]
print(f"   Total labels printed: {label_count}")

# 5. Any suspicious status?
print("\n5. Status breakdown for orders on this date:")
cur.execute("""
    SELECT status_normalized, COUNT(*)
    FROM order_header
    WHERE DATE(collection_time AT TIME ZONE 'Asia/Bangkok') = %s
    GROUP BY status_normalized
    ORDER BY COUNT(*) DESC
""", (target_date,))
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]}")

cur.close()
conn.close()
