"""Backfill courier_code for Lazada orders from raw_payload"""
import psycopg2
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
print("BACKFILL courier_code FOR LAZADA ORDERS")
print("=" * 70)

# Fetch Lazada orders without courier
cur.execute("""
    SELECT id, raw_payload
    FROM order_header 
    WHERE channel_code = 'lazada'
      AND (courier_code IS NULL OR courier_code = '')
      AND raw_payload IS NOT NULL
""")

updated = 0
skipped = 0

for row in cur.fetchall():
    order_id = row[0]
    raw = row[1]
    
    if not isinstance(raw, dict):
        skipped += 1
        continue
    
    # Get courier from order_items[0].shipment_provider
    courier = None
    tracking = None
    items = raw.get("order_items", [])
    if items:
        first_item = items[0]
        courier = first_item.get("shipment_provider")
        tracking = first_item.get("tracking_code") or first_item.get("tracking_number")
    
    if courier:
        if tracking:
            cur.execute("""
                UPDATE order_header 
                SET courier_code = %s, tracking_number = %s 
                WHERE id = %s
            """, (courier, tracking, order_id))
        else:
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

# Verify
print("\n" + "=" * 70)
print("VERIFY: Lazada Orders after backfill")
print("=" * 70)
cur.execute("""
    SELECT 
        COALESCE(courier_code, '(NULL)') as courier,
        COUNT(*) as count
    FROM order_header 
    WHERE channel_code = 'lazada'
    GROUP BY courier_code 
    ORDER BY count DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0]:30} : {row[1]:6} orders")

cur.close()
conn.close()
print("\n[OK] Done!")
