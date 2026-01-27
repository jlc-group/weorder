"""
Data Integrity Verification Script
ตรวจสอบความถูกต้องของข้อมูลใน Database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.core.database import SessionLocal
from app.models import OrderHeader, OrderItem, Product, StockLedger
from app.models.master import Warehouse
from sqlalchemy import func, text
from datetime import datetime, timedelta

db = SessionLocal()

print('=' * 70)
print('WeOrder Data Integrity Report')
print(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('=' * 70)

# ============================================================
# 1. DATABASE SUMMARY
# ============================================================
print('\n[1] DATABASE SUMMARY')
print('-' * 50)

total_orders = db.query(func.count(OrderHeader.id)).scalar()
total_products = db.query(func.count(Product.id)).scalar()
total_stock_movements = db.query(func.count(StockLedger.id)).scalar()
total_order_items = db.query(func.count(OrderItem.id)).scalar()

print(f'  Orders (order_header): {total_orders:,}')
print(f'  Order Items (order_item): {total_order_items:,}')
print(f'  Products (product): {total_products:,}')
print(f'  Stock Movements (stock_ledger): {total_stock_movements:,}')

# ============================================================
# 2. ORDER STATUS DISTRIBUTION
# ============================================================
print('\n[2] ORDER STATUS DISTRIBUTION')
print('-' * 50)

status_results = db.query(
    OrderHeader.status_normalized,
    func.count(OrderHeader.id)
).group_by(OrderHeader.status_normalized).order_by(func.count(OrderHeader.id).desc()).all()

for status, count in status_results:
    pct = (100 * count / total_orders) if total_orders else 0
    print(f'  {status or "NULL"}: {count:,} ({pct:.1f}%)')

# ============================================================
# 3. ORDERS BY CHANNEL
# ============================================================
print('\n[3] ORDERS BY CHANNEL (Platform)')
print('-' * 50)

channel_results = db.query(
    OrderHeader.channel_code,
    func.count(OrderHeader.id)
).group_by(OrderHeader.channel_code).order_by(func.count(OrderHeader.id).desc()).all()

for channel, count in channel_results:
    pct = (100 * count / total_orders) if total_orders else 0
    print(f'  {channel}: {count:,} ({pct:.1f}%)')

# ============================================================
# 4. DATA INTEGRITY CHECKS
# ============================================================
print('\n[4] DATA INTEGRITY CHECKS')
print('-' * 50)

# 4.1 Orders without items
orders_no_items = db.query(func.count(OrderHeader.id)).filter(
    ~OrderHeader.id.in_(
        db.query(OrderItem.order_id).distinct()
    )
).scalar()
print(f'  [?] Orders without items: {orders_no_items:,}')

# 4.2 Order items with NULL product_id
items_null_product = db.query(func.count(OrderItem.id)).filter(
    OrderItem.product_id.is_(None)
).scalar()
print(f'  [?] Order items without product_id: {items_null_product:,}')

# 4.3 Products not in any order
products_no_orders = db.query(func.count(Product.id)).filter(
    ~Product.id.in_(
        db.query(OrderItem.product_id).distinct()
    )
).scalar()
print(f'  [i] Products never ordered: {products_no_orders:,}')

# 4.4 Stock balance check (sum of movements per product)
print('\n[5] STOCK BALANCE CHECK')
print('-' * 50)

stock_balance = db.query(
    Product.sku,
    Product.name,
    func.sum(StockLedger.quantity).label('balance')
).join(StockLedger, Product.id == StockLedger.product_id
).group_by(Product.id, Product.sku, Product.name
).order_by(func.sum(StockLedger.quantity)).limit(10).all()

negative_count = 0
for sku, name, balance in stock_balance:
    if balance < 0:
        negative_count += 1
        name_short = name[:30] if name else 'N/A'
        print(f'  [!] {sku}: {balance:,} ({name_short}...)')

if negative_count == 0:
    print('  [OK] No negative stock found in top 10 lowest')
else:
    print(f'\n  Total with negative balance shown: {negative_count}')

# Count all negative
all_negative = db.query(func.count()).select_from(
    db.query(
        func.sum(StockLedger.quantity).label('bal')
    ).group_by(StockLedger.product_id).having(func.sum(StockLedger.quantity) < 0).subquery()
).scalar()
print(f'  Total products with negative stock: {all_negative or 0}')

# ============================================================
# 6. RECENT ACTIVITY (Last 7 days)
# ============================================================
print('\n[6] RECENT ACTIVITY (Last 7 days)')
print('-' * 50)

seven_days_ago = datetime.now() - timedelta(days=7)

recent_orders = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.created_at >= seven_days_ago
).scalar()
print(f'  New orders: {recent_orders:,}')

recent_stock = db.query(func.count(StockLedger.id)).filter(
    StockLedger.created_at >= seven_days_ago
).scalar()
print(f'  Stock movements: {recent_stock:,}')

# ============================================================
# 7. KEY DATE FIELDS COVERAGE
# ============================================================
print('\n[7] DATE FIELDS COVERAGE')
print('-' * 50)

date_fields = [
    ('order_datetime', OrderHeader.order_datetime),
    ('paid_time', OrderHeader.paid_time),
    ('rts_time', OrderHeader.rts_time),
    ('shipped_at', OrderHeader.shipped_at),
    ('collection_time', OrderHeader.collection_time),
]

for field_name, field in date_fields:
    with_value = db.query(func.count(OrderHeader.id)).filter(field.isnot(None)).scalar()
    pct = (100 * with_value / total_orders) if total_orders else 0
    print(f'  {field_name}: {with_value:,} ({pct:.1f}%)')

# ============================================================
# 8. SUMMARY
# ============================================================
print('\n' + '=' * 70)
print('SUMMARY')
print('=' * 70)

issues = []
if orders_no_items > 0:
    issues.append(f'Orders without items: {orders_no_items}')
if items_null_product > 100:
    issues.append(f'Many order items without product_id: {items_null_product}')
if all_negative and all_negative > 0:
    issues.append(f'Products with negative stock: {all_negative}')

if issues:
    print('[!] ISSUES TO REVIEW:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('[OK] No critical data integrity issues found')

print('\n' + '=' * 70)
db.close()
