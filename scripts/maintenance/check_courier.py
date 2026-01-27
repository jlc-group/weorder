"""Final verification of ALL platforms courier data"""
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

print("=" * 70)
print("FINAL VERIFICATION: ALL PLATFORMS (PAID/PACKING/RTS Orders)")
print("=" * 70)

cur.execute("""
    SELECT 
        channel_code,
        COUNT(*) as total,
        COUNT(CASE WHEN courier_code IS NOT NULL AND courier_code != '' THEN 1 END) as has_courier,
        ROUND(100.0 * COUNT(CASE WHEN courier_code IS NOT NULL AND courier_code != '' THEN 1 END) / NULLIF(COUNT(*), 0), 1) as pct
    FROM order_header 
    WHERE status_normalized IN ('PAID', 'PACKING', 'READY_TO_SHIP')
    GROUP BY channel_code 
    ORDER BY total DESC
""")
print(f"{'Platform':<15} {'Total':>10} {'Has Courier':>15} {'%':>8}")
print("-" * 55)
for row in cur.fetchall():
    pct = row[3] if row[3] else 0
    print(f"{row[0] or 'NULL':<15} {row[1]:>10} {row[2]:>15} {pct:>7}%")

print("\n" + "=" * 70)
print("READY_TO_SHIP ORDERS BY COURIER (All Platforms)")
print("=" * 70)

cur.execute("""
    SELECT 
        COALESCE(courier_code, '(NULL)') as courier,
        COUNT(*) as count
    FROM order_header 
    WHERE status_normalized = 'READY_TO_SHIP'
    GROUP BY courier_code 
    ORDER BY count DESC
    LIMIT 15
""")
print(f"{'Courier':<40} {'Count':>10}")
print("-" * 55)
for row in cur.fetchall():
    print(f"{row[0][:39]:<40} {row[1]:>10}")

print("\n" + "=" * 70)
print("SUMMARY: Before vs After Fix")
print("=" * 70)
cur.execute("""
    SELECT 
        COUNT(*) as total_rts,
        COUNT(CASE WHEN courier_code IS NOT NULL AND courier_code != '' THEN 1 END) as with_courier
    FROM order_header 
    WHERE status_normalized IN ('PAID', 'PACKING', 'READY_TO_SHIP')
""")
row = cur.fetchone()
pct = (row[1] / row[0] * 100) if row[0] > 0 else 0
print(f"Total PAID/PACKING/RTS Orders: {row[0]}")
print(f"With Courier: {row[1]} ({pct:.1f}%)")

cur.close()
conn.close()
print("\n[OK] Done!")
