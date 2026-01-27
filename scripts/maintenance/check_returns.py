"""Analyze Return/Delivery Failed orders - Stock impact"""
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
print("1. RETURN-RELATED ORDERS SUMMARY")
print("=" * 70)

cur.execute("""
    SELECT status_normalized, COUNT(*) as count
    FROM order_header 
    WHERE status_normalized IN ('DELIVERY_FAILED', 'TO_RETURN', 'RETURNED')
    GROUP BY status_normalized 
    ORDER BY count DESC
""")
total = 0
for row in cur.fetchall():
    print(f"  {row[0]:<20} : {row[1]:>6} orders")
    total += row[1]
print(f"  {'TOTAL':20} : {total:>6} orders")

print("\n" + "=" * 70)
print("2. CHECK: Stock Ledger for RETURNED orders")
print("=" * 70)

# Check stock_ledger structure
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'stock_ledger' 
    ORDER BY ordinal_position
""")
print("stock_ledger columns:", [r[0] for r in cur.fetchall()])

# Check for stock movements related to orders
cur.execute("""
    SELECT movement_type, COUNT(*) 
    FROM stock_ledger 
    WHERE reference_type = 'ORDER'
    GROUP BY movement_type
""")
print("\nStock movements by type (ORDER-related):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n" + "=" * 70)
print("3. SHIPPED vs RETURNED Stock Balance")
print("=" * 70)

# Count SHIPPED orders that had stock deducted
cur.execute("""
    SELECT COUNT(DISTINCT reference_id) 
    FROM stock_ledger 
    WHERE reference_type = 'ORDER' AND movement_type = 'OUT'
""")
shipped_out = cur.fetchone()[0]

# Count RETURNED orders that had stock returned
cur.execute("""
    SELECT COUNT(DISTINCT reference_id) 
    FROM stock_ledger 
    WHERE reference_type = 'ORDER' AND movement_type = 'IN'
""")
returned_in = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM order_header WHERE status_normalized = 'RETURNED'
""")
returned_orders = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM order_header WHERE status_normalized = 'DELIVERY_FAILED'
""")
delivery_failed = cur.fetchone()[0]

print(f"  Orders with Stock OUT (SHIPPED): {shipped_out}")
print(f"  Orders with Stock IN (RETURNED): {returned_in}")
print(f"  RETURNED orders in DB: {returned_orders}")
print(f"  DELIVERY_FAILED orders in DB: {delivery_failed}")

print("\n" + "=" * 70)
print("4. GAP ANALYSIS")
print("=" * 70)
gap = (returned_orders + delivery_failed) - returned_in
print(f"""
  อธิบาย:
  - สินค้าที่ส่งออก (SHIPPED) = ตัดสต็อก (OUT) ✅
  - สินค้าที่ตีคืน (RETURNED) = เพิ่มสต็อกกลับ (IN) ✅
  - สินค้าที่ส่งไม่สำเร็จ (DELIVERY_FAILED) = ❓
  
  ปัญหา:
  - DELIVERY_FAILED {delivery_failed} orders
  - แต่มี stock IN เพียง {returned_in} orders
  - ⚠️ GAP: ~{gap} orders อาจต้องเพิ่มสต็อกกลับ
""")

print("=" * 70)
print("5. RECOMMENDATION")
print("=" * 70)
print("""
ต้องแก้ไข order_service.py:
  - เมื่อ status เปลี่ยนเป็น DELIVERY_FAILED → Stock IN
  - เมื่อ status เปลี่ยนเป็น RETURNED → Stock IN (มีแล้ว)
  - เพิ่ม return_reason field เพื่อแยกประเภท
""")

cur.close()
conn.close()
print("\n[OK] Done!")
