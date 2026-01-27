"""Backfill returned_at from raw_payload cancel_time (actual return date)"""
import psycopg2
from datetime import datetime, timezone
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
print("BACKFILL returned_at FROM raw_payload.cancel_time")
print("=" * 70)

# Get TikTok orders with cancel_time in raw_payload
cur.execute("""
    SELECT id, external_order_id, raw_payload->'cancel_time' as cancel_time, returned_at
    FROM order_header 
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND channel_code = 'tiktok'
      AND raw_payload->>'cancel_time' IS NOT NULL
""")

orders = cur.fetchall()
print(f"TikTok orders with cancel_time: {len(orders)}")

updated = 0
for order_id, ext_id, cancel_time, current_returned_at in orders:
    try:
        # Convert Unix timestamp to datetime
        if cancel_time:
            ts = int(cancel_time)
            new_returned_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            
            # Update if different from current
            cur.execute("""
                UPDATE order_header 
                SET returned_at = %s
                WHERE id = %s
            """, (new_returned_at, order_id))
            updated += 1
    except Exception as e:
        print(f"  Error for {ext_id}: {e}")

conn.commit()
print(f"✅ Updated: {updated} orders")

# Also check Shopee (different field names)
print("\n" + "-" * 50)
print("Checking Shopee orders...")

cur.execute("""
    SELECT id, external_order_id, raw_payload
    FROM order_header 
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND channel_code = 'shopee'
      AND raw_payload IS NOT NULL
""")

shopee_updated = 0
for order_id, ext_id, raw in cur.fetchall():
    try:
        if isinstance(raw, dict):
            # Shopee may have update_time or cancel_time
            cancel_time = raw.get('cancel_time') or raw.get('update_time')
            if cancel_time and isinstance(cancel_time, int) and cancel_time > 1600000000:
                new_returned_at = datetime.fromtimestamp(cancel_time, tz=timezone.utc)
                cur.execute("""
                    UPDATE order_header 
                    SET returned_at = %s
                    WHERE id = %s
                """, (new_returned_at, order_id))
                shopee_updated += 1
    except Exception as e:
        pass

conn.commit()
print(f"✅ Updated Shopee: {shopee_updated} orders")

# Verify
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

cur.execute("""
    SELECT 
        external_order_id,
        status_normalized,
        return_reason,
        returned_at,
        order_datetime
    FROM order_header 
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
    ORDER BY returned_at DESC
    LIMIT 10
""")

print(f"{'Order ID':<25} {'Ordered':<20} {'Returned':<20}")
print("-" * 70)
for row in cur.fetchall():
    ordered = str(row[4])[:10] if row[4] else "NULL"
    returned = str(row[3])[:10] if row[3] else "NULL"
    print(f"{row[0]:<25} {ordered:<20} {returned:<20}")

cur.close()
conn.close()
print("\n[OK] Done!")
