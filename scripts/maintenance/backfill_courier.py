"""Backfill courier_code from raw_payload for TikTok orders"""
import psycopg2
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host="192.168.0.41",
    database="weorder_db",
    user="weorder_user",
    password="sZ3vlr2tzjz5x#T8",
    port=5432
)
conn.autocommit = False
cur = conn.cursor()

print("=" * 70)
print("BACKFILL courier_code FROM raw_payload")
print("=" * 70)

# Count orders that need update
cur.execute("""
    SELECT COUNT(*) 
    FROM order_header 
    WHERE channel_code = 'tiktok'
      AND (courier_code IS NULL OR courier_code = '')
      AND raw_payload IS NOT NULL
      AND raw_payload::text LIKE '%shipping_provider%'
""")
count = cur.fetchone()[0]
print(f"Orders to update: {count}")

if count == 0:
    print("No orders need updating!")
    cur.close()
    conn.close()
    exit()

# Fetch orders that need update
cur.execute("""
    SELECT id, raw_payload
    FROM order_header 
    WHERE channel_code = 'tiktok'
      AND (courier_code IS NULL OR courier_code = '')
      AND raw_payload IS NOT NULL
    LIMIT 50000
""")

updated = 0
skipped = 0

for row in cur.fetchall():
    order_id = row[0]
    raw = row[1]
    
    if not isinstance(raw, dict):
        skipped += 1
        continue
    
    # Try to get courier from shipping_provider (primary) or packages (fallback)
    courier = raw.get("shipping_provider")
    if not courier:
        packages = raw.get("packages", [])
        if packages:
            courier = packages[0].get("shipping_provider_name")
    
    if courier:
        cur.execute("""
            UPDATE order_header 
            SET courier_code = %s 
            WHERE id = %s
        """, (courier, order_id))
        updated += 1
    else:
        skipped += 1

conn.commit()
print(f"\n✅ Updated: {updated}")
print(f"⏭️ Skipped (no courier in payload): {skipped}")

# Verify results
print("\n" + "=" * 70)
print("VERIFY: TikTok Orders courier_code after update")
print("=" * 70)
cur.execute("""
    SELECT 
        CASE WHEN courier_code IS NULL OR courier_code = '' THEN '(NULL/Empty)' ELSE courier_code END as courier,
        COUNT(*) as count
    FROM order_header 
    WHERE channel_code = 'tiktok'
    GROUP BY courier_code 
    ORDER BY count DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]:30} : {row[1]:6} orders")

cur.close()
conn.close()
print("\n[OK] Done!")
