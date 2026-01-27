"""Add return tracking columns to order_header table"""
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
conn.autocommit = True
cur = conn.cursor()

print("=" * 70)
print("ADD RETURN TRACKING COLUMNS")
print("=" * 70)

columns_to_add = [
    ("returned_at", "TIMESTAMP WITH TIME ZONE"),
    ("return_reason", "VARCHAR(50)"),
    ("return_verified", "BOOLEAN DEFAULT FALSE"),
    ("return_verified_by", "UUID"),
    ("return_notes", "TEXT"),
]

for col_name, col_type in columns_to_add:
    try:
        cur.execute(f"ALTER TABLE order_header ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        print(f"  ✅ Added: {col_name} ({col_type})")
    except Exception as e:
        print(f"  ❌ Error adding {col_name}: {e}")

# Backfill returned_at from updated_at for existing RETURNED/DELIVERY_FAILED orders
print("\n" + "-" * 50)
print("Backfilling returned_at for existing orders...")

cur.execute("""
    UPDATE order_header 
    SET returned_at = updated_at,
        return_reason = CASE 
            WHEN status_normalized = 'DELIVERY_FAILED' THEN 'DELIVERY_FAILED'
            WHEN status_normalized = 'RETURNED' THEN 'CUSTOMER_RETURN'
            ELSE NULL
        END
    WHERE status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND returned_at IS NULL
""")
print(f"  Updated {cur.rowcount} orders")

# Verify
print("\n" + "-" * 50)
print("Verification:")
cur.execute("""
    SELECT return_reason, COUNT(*), 
           MIN(returned_at), MAX(returned_at)
    FROM order_header 
    WHERE returned_at IS NOT NULL
    GROUP BY return_reason
""")
print(f"{'Reason':<20} {'Count':>8} {'Earliest':>25} {'Latest':>25}")
for row in cur.fetchall():
    print(f"{row[0] or 'NULL':<20} {row[1]:>8} {str(row[2])[:19]:>25} {str(row[3])[:19]:>25}")

cur.close()
conn.close()
print("\n[OK] Done!")
