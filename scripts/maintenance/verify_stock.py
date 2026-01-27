"""Final verification of return stock logic"""
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
print("FINAL VERIFICATION: Return Stock Logic")
print("=" * 70)

# Stock movements summary
cur.execute("""
    SELECT movement_type, COUNT(*) 
    FROM stock_ledger 
    WHERE reference_type = 'ORDER'
    GROUP BY movement_type
""")
print("\nStock Movements (ORDER-related):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check RETURNED/DELIVERY_FAILED orders coverage
print("\n" + "-" * 50)
print("RETURNED/DELIVERY_FAILED Orders Stock Coverage:")

cur.execute("""
    SELECT 
        oh.status_normalized,
        COUNT(*) as total,
        COUNT(DISTINCT sl.reference_id) as with_stock_in
    FROM order_header oh
    LEFT JOIN stock_ledger sl ON sl.reference_id = oh.id::text 
        AND sl.movement_type = 'IN' 
        AND sl.reference_type = 'ORDER'
    WHERE oh.status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
    GROUP BY oh.status_normalized
""")
for row in cur.fetchall():
    pct = (row[2] / row[1] * 100) if row[1] > 0 else 0
    print(f"  {row[0]:<20} {row[1]:>6} orders, {row[2]:>6} with stock IN ({pct:.1f}%)")

# Sample stock IN entries
print("\n" + "-" * 50)
print("Recent Stock IN (Returns):")
cur.execute("""
    SELECT note, quantity, created_at
    FROM stock_ledger 
    WHERE reference_type = 'ORDER' AND movement_type = 'IN'
    ORDER BY created_at DESC
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  {row[2]} | {row[0]} | qty: {row[1]}")

cur.close()
conn.close()
print("\n[OK] Done!")
