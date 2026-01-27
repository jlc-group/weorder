"""
Backfill stock for DELIVERY_FAILED and RETURNED orders that are missing stock IN movements.

This script:
1. Finds orders with status DELIVERY_FAILED or RETURNED
2. Checks if they already have a stock IN movement
3. If not, creates stock IN movements for each item

Run with: python backfill_return_stock.py
"""
import psycopg2
from uuid import uuid4
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
conn.autocommit = False
cur = conn.cursor()

print("=" * 70)
print("BACKFILL STOCK FOR RETURNED/DELIVERY_FAILED ORDERS")
print("=" * 70)

# Find orders that need stock return and don't have it yet
cur.execute("""
    SELECT oh.id, oh.external_order_id, oh.status_normalized, oh.warehouse_id
    FROM order_header oh
    WHERE oh.status_normalized IN ('RETURNED', 'DELIVERY_FAILED')
      AND NOT EXISTS (
          SELECT 1 FROM stock_ledger sl 
          WHERE sl.reference_id = oh.id::text 
            AND sl.reference_type = 'ORDER'
            AND sl.movement_type = 'IN'
      )
""")

orders_to_update = cur.fetchall()
print(f"Orders needing stock return: {len(orders_to_update)}")

if len(orders_to_update) == 0:
    print("No orders need updating!")
    cur.close()
    conn.close()
    exit()

print(f"\nProceeding with {len(orders_to_update)} orders...")

updated = 0
skipped = 0
errors = 0

for order_id, ext_id, status, warehouse_id in orders_to_update:
    try:
        # Get order items with product_id
        cur.execute("""
            SELECT oi.product_id, oi.quantity, oi.sku
            FROM order_item oi
            WHERE oi.order_id = %s
              AND oi.product_id IS NOT NULL
        """, (order_id,))
        
        items = cur.fetchall()
        
        if not items:
            skipped += 1
            continue
        
        # Create stock IN for each item
        return_reason = "Delivery Failed" if status == "DELIVERY_FAILED" else "Returned"
        
        for product_id, quantity, sku in items:
            if not product_id or not warehouse_id:
                continue
                
            cur.execute("""
                INSERT INTO stock_ledger 
                (id, warehouse_id, product_id, movement_type, quantity, reference_type, reference_id, note, created_at)
                VALUES (%s, %s, %s, 'IN', %s, 'ORDER', %s, %s, %s)
            """, (
                str(uuid4()),
                str(warehouse_id),
                str(product_id),
                quantity,
                str(order_id),
                f"[Backfill] Order {return_reason}: {ext_id}",
                datetime.now()
            ))
        
        updated += 1
        
        if updated % 100 == 0:
            print(f"  Progress: {updated} orders updated...")
            conn.commit()
            
    except Exception as e:
        errors += 1
        print(f"  Error for {ext_id}: {e}")

conn.commit()

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"✅ Updated: {updated}")
print(f"⏭️ Skipped (no items): {skipped}")
print(f"❌ Errors: {errors}")

# Verify
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)
cur.execute("""
    SELECT movement_type, COUNT(*) 
    FROM stock_ledger 
    WHERE reference_type = 'ORDER'
    GROUP BY movement_type
""")
print("Stock movements (ORDER-related) after backfill:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
print("\n[OK] Done!")
