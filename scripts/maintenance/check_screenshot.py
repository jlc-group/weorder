"""Check specific orders from TikTok screenshot"""
import psycopg2
from datetime import datetime
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

# Order IDs from screenshot (sorted oldest first)
order_ids = [
    '581867667035096570',  # วันที่ 9:36:04
    '581867674275841117',  # วันที่ 9:56:58
    '581867675487601796',  # วันที่ 9:37:29
    '582041336214291870',  # วันที่ 11:24:47
]

print("=== Checking Orders from Screenshot ===\n")

for oid in order_ids:
    cur.execute("""
        SELECT external_order_id, order_datetime, status_normalized, created_at
        FROM order_header
        WHERE external_order_id = %s
    """, (oid,))
    row = cur.fetchone()
    if row:
        print(f"Order: {row[0]}")
        print(f"  Order Date: {row[1]}")
        print(f"  Status: {row[2]}")
        print(f"  Synced At: {row[3]}")
        print()
    else:
        print(f"Order: {oid} - NOT FOUND in WeOrder!")
        print()

# Find oldest PAID order
print("\n=== Oldest PAID Orders ===")
cur.execute("""
    SELECT external_order_id, order_datetime, status_normalized
    FROM order_header
    WHERE channel_code = 'tiktok' AND status_normalized = 'PAID'
    ORDER BY order_datetime ASC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]}")

cur.close()
conn.close()
