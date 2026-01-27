"""Check specific order return data"""
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
cur = conn.cursor()

# Check this specific order 
cur.execute("""
    SELECT 
        external_order_id,
        status_normalized,
        returned_at,
        return_reason,
        return_verified,
        updated_at,
        channel_code
    FROM order_header 
    WHERE external_order_id = '582190878595384828'
""")
row = cur.fetchone()
if row:
    print(f"Order: {row[0]}")
    print(f"Status: {row[1]}")
    print(f"returned_at: {row[2]}")
    print(f"return_reason: {row[3]}")
    print(f"return_verified: {row[4]}")
    print(f"updated_at: {row[5]}")
    print(f"channel: {row[6]}")
else:
    print("Order not found")

# Count orders with NULL returned_at
print("\n" + "=" * 50)
print("Orders with NULL returned_at despite RETURNED/DELIVERY_FAILED status:")
cur.execute("""
    SELECT status_normalized, COUNT(*) 
    FROM order_header 
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND returned_at IS NULL
    GROUP BY status_normalized
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} orders missing returned_at")

# Total with returned_at
cur.execute("""
    SELECT status_normalized, COUNT(*) 
    FROM order_header 
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND returned_at IS NOT NULL
    GROUP BY status_normalized
""")
print("\nOrders WITH returned_at:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} orders have returned_at")

cur.close()
conn.close()
