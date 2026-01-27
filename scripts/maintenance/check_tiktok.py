"""Check TikTok order counts"""
import psycopg2
from datetime import datetime, date, timedelta
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

today = date.today()

print(f"=== TikTok Order Analysis - {today} ===\n")

# 1. Today's TikTok orders by status
print("1. Today's TikTok Orders by Status:")
cur.execute("""
    SELECT status_normalized, COUNT(*) 
    FROM order_header
    WHERE channel_code = 'tiktok'
      AND DATE(order_datetime AT TIME ZONE 'Asia/Bangkok') = %s
    GROUP BY status_normalized
    ORDER BY COUNT(*) DESC
""", (today,))
total_today = 0
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]}")
    total_today += row[1]
print(f"   TOTAL: {total_today}")

# 2. Last 7 days trend
print("\n2. TikTok Orders Last 7 Days:")
for i in range(7):
    check_date = today - timedelta(days=i)
    cur.execute("""
        SELECT COUNT(*) FROM order_header
        WHERE channel_code = 'tiktok'
          AND DATE(order_datetime AT TIME ZONE 'Asia/Bangkok') = %s
    """, (check_date,))
    count = cur.fetchone()[0]
    print(f"   {check_date}: {count}")

# 3. Last sync time
print("\n3. Last TikTok Order Synced:")
cur.execute("""
    SELECT external_order_id, order_datetime, created_at, status_normalized
    FROM order_header
    WHERE channel_code = 'tiktok'
    ORDER BY created_at DESC
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"   {row[0]} | Order: {row[1]} | Synced: {row[2]} | {row[3]}")

# 4. Check for gaps in order IDs
print("\n4. Hour-by-hour breakdown for today:")
cur.execute("""
    SELECT 
        EXTRACT(HOUR FROM order_datetime AT TIME ZONE 'Asia/Bangkok') as hour,
        COUNT(*) 
    FROM order_header
    WHERE channel_code = 'tiktok'
      AND DATE(order_datetime AT TIME ZONE 'Asia/Bangkok') = %s
    GROUP BY EXTRACT(HOUR FROM order_datetime AT TIME ZONE 'Asia/Bangkok')
    ORDER BY hour
""", (today,))
for row in cur.fetchall():
    print(f"   {int(row[0]):02d}:00 - {row[1]} orders")

cur.close()
conn.close()
