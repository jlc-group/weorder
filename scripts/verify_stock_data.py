"""
Stock Data Verification Script
Checks StockLedger entries and current order data
"""
from app.core.database import SessionLocal
from app.models import OrderHeader, OrderItem, Product
from app.models.stock import StockLedger
from app.services.stock_service import StockService
from sqlalchemy import func, and_, desc
from datetime import datetime, time, timedelta

db = SessionLocal()

print('=' * 70)
print('STOCK DATA VERIFICATION REPORT')
print(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('=' * 70)

# 1. StockLedger Summary
print('\n[1] STOCK LEDGER SUMMARY')
print('-' * 50)
ledger_stats = db.query(
    StockLedger.movement_type,
    func.count(StockLedger.id).label('count'),
    func.sum(StockLedger.quantity).label('total_qty')
).group_by(StockLedger.movement_type).all()

for movement_type, count, total_qty in ledger_stats:
    print(f'  {movement_type}: {count} entries, total qty: {total_qty}')

total_ledger = db.query(func.count(StockLedger.id)).scalar()
print(f'  TOTAL ENTRIES: {total_ledger}')

# 2. Recent Stock Movements (last 10)
print('\n[2] RECENT STOCK MOVEMENTS (Last 10)')
print('-' * 50)
recent = db.query(StockLedger).order_by(desc(StockLedger.created_at)).limit(10).all()
for r in recent:
    product = db.query(Product).filter(Product.id == r.product_id).first()
    sku = product.sku if product else 'UNKNOWN'
    print(f'  {r.created_at.strftime("%Y-%m-%d %H:%M")} | {r.movement_type:8} | {sku:15} | qty: {r.quantity:+6} | ref: {r.reference_type or "-"}')

# 3. Current Stock Summary (Top 10 products)
print('\n[3] CURRENT STOCK SUMMARY (Top 10 by on-hand)')
print('-' * 50)
stock_summary = StockService.get_stock_summary(db)
stock_summary_sorted = sorted(stock_summary, key=lambda x: x.get('on_hand', 0), reverse=True)[:10]
print(f'  {"SKU":<20} {"On-Hand":>10} {"Reserved":>10} {"Available":>10}')
print(f'  {"-"*20} {"-"*10} {"-"*10} {"-"*10}')
for item in stock_summary_sorted:
    print(f'  {item["sku"]:<20} {item["on_hand"]:>10} {item["reserved"]:>10} {item["available"]:>10}')

# 4. Orders Status Summary
print('\n[4] ORDERS STATUS SUMMARY')
print('-' * 50)
order_stats = db.query(
    OrderHeader.status_normalized,
    func.count(OrderHeader.id)
).group_by(OrderHeader.status_normalized).all()

total_orders = 0
for status, count in sorted(order_stats, key=lambda x: x[1], reverse=True):
    print(f'  {status or "NULL":<25}: {count:>6}')
    total_orders += count
print(f'  {"TOTAL":<25}: {total_orders:>6}')

# 5. Recent Orders (last 24 hours)
print('\n[5] RECENT ORDERS (Last 24 hours)')
print('-' * 50)
yesterday = datetime.now() - timedelta(hours=24)
recent_orders = db.query(
    OrderHeader.channel_code,
    OrderHeader.status_normalized,
    func.count(OrderHeader.id)
).filter(
    OrderHeader.updated_at >= yesterday
).group_by(
    OrderHeader.channel_code,
    OrderHeader.status_normalized
).all()

print(f'  {"Platform":<15} {"Status":<20} {"Count":>10}')
print(f'  {"-"*15} {"-"*20} {"-"*10}')
for platform, status, count in sorted(recent_orders, key=lambda x: (x[0] or '', x[1] or '')):
    print(f'  {platform or "-":<15} {status or "-":<20} {count:>10}')

# 6. Stock Deduction Check - Orders that are RTS but no OUT movement
print('\n[6] STOCK DEDUCTION VERIFICATION')
print('-' * 50)

# Count RTS orders
rts_count = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.status_normalized == 'READY_TO_SHIP'
).scalar()

# Count OUT movements
out_movements = db.query(func.count(StockLedger.id)).filter(
    StockLedger.movement_type == 'OUT'
).scalar()

print(f'  Total RTS Orders: {rts_count}')
print(f'  Total OUT Movements: {out_movements}')

# Check for orders with reference in ledger
orders_with_deduction = db.query(func.count(func.distinct(StockLedger.reference_id))).filter(
    StockLedger.reference_type == 'order',
    StockLedger.movement_type == 'OUT'
).scalar()
print(f'  Orders with Stock Deduction: {orders_with_deduction}')

# 7. Today's Activity
print('\n[7] TODAY\'S ACTIVITY')
print('-' * 50)
today = datetime.now().date()
start_today = datetime.combine(today, time.min)
end_today = datetime.combine(today, time.max)

today_orders = db.query(func.count(OrderHeader.id)).filter(
    OrderHeader.created_at >= start_today,
    OrderHeader.created_at <= end_today
).scalar()

today_movements = db.query(func.count(StockLedger.id)).filter(
    StockLedger.created_at >= start_today,
    StockLedger.created_at <= end_today
).scalar()

print(f'  New Orders Today: {today_orders}')
print(f'  Stock Movements Today: {today_movements}')

# 8. Data Integrity Check
print('\n[8] DATA INTEGRITY CHECK')
print('-' * 50)

# Products without stock entries
products_count = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar()
products_with_stock = db.query(func.count(func.distinct(StockLedger.product_id))).scalar()
print(f'  Active Products: {products_count}')
print(f'  Products with Stock Entries: {products_with_stock}')
print(f'  Products without Stock Data: {products_count - products_with_stock}')

# Orders without items
orders_without_items = db.query(func.count(OrderHeader.id)).filter(
    ~OrderHeader.id.in_(db.query(func.distinct(OrderItem.order_id)))
).scalar()
print(f'  Orders without Items: {orders_without_items}')

print('\n' + '=' * 70)
print('VERIFICATION COMPLETE')
print('=' * 70)

db.close()
