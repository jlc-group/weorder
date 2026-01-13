
import psycopg2
import sys
import time

DB_CONFIG = {
    "dbname": "weorder",
    "user": "chanack",
    "password": "chanack",
    "host": "localhost",
    "port": "5432"
}

def backfill_profit_fees():
    """Aggregate fees from marketplace_transaction and update order_profit"""
    print("Starting Finance Profit Backfill...", flush=True)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. Aggregate fees per order_id
    # We include COMMISSION_FEE, SERVICE_FEE, TRANSACTION_FEE, etc.
    # Note: amounts in marketplace_transaction are negative for fees.
    # We use ABS() to store as positive cost in order_profit.
    
    agg_sql = """
    UPDATE order_profit op SET
        platform_fee_total = fees.total_fees,
        net_profit = op.gross_profit - fees.total_fees,
        calculated_at = NOW()
    FROM (
        SELECT 
            order_id,
            SUM(ABS(amount)) as total_fees
        FROM marketplace_transaction
        WHERE transaction_type IN (
            'COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 
            'PAYMENT_FEE', 'COIN_CASHBACK_FEE', 'MARKETING_BENEFITS_PACKAGE_FEE',
            'DEDUCTIONS_INCURRED_BY_SELLER', 'ADJUSTMENT', 'SHIPPING_FEE'
        )
        AND order_id IS NOT NULL
        GROUP BY order_id
    ) fees
    WHERE op.order_id = fees.order_id;
    """
    
    print("Executing aggregation and update of platform_fee_total in order_profit...", flush=True)
    start = time.time()
    cur.execute(agg_sql)
    count = cur.rowcount
    conn.commit()
    print(f"Updated {count} order_profit records in {time.time() - start:.2f}s", flush=True)
    
    # 2. Re-calculate profit_margin_percent
    # margin = (net_profit / total_revenue) * 100
    margin_sql = """
    UPDATE order_profit SET
        profit_margin_percent = CASE 
            WHEN total_revenue > 0 THEN LEAST(GREATEST((net_profit / total_revenue) * 100, -9999.99), 9999.99)
            ELSE 0 END
    WHERE total_revenue IS NOT NULL;
    """
    print("Re-calculating profit margins...", flush=True)
    cur.execute(margin_sql)
    conn.commit()
    
    conn.close()

if __name__ == "__main__":
    backfill_profit_fees()
    print("\n✅ Finance profit backfill complete!", flush=True)
