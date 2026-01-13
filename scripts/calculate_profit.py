
import psycopg2
from psycopg2.extras import Json
import sys
import time

# DB Configuration
DB_CONFIG = {
    "dbname": "weorder",
    "user": "chanack",
    "password": "chanack",
    "host": "localhost",
    "port": "5432"
}

BATCH_SIZE = 10000

def run_profit_calculation():
    print("Starting Profit Calculation...", flush=True)
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Connected to DB.", flush=True)

        # SQL to Calculate and Upsert Order Profit
        # Using a single massive Insert-Select might be slow or lock too much row, 
        # but for ~1M rows it might take a minute. Let's try batching or just one go?
        # A single query is atomic and consistent. 
        # But let's process in chunks if possible? No, generating the profit based on IDs is cleaner.
        # Actually, let's just run it as one big query but optimized.
        
        upsert_sql = """
        INSERT INTO order_profit (
            order_id,
            company_id,
            total_revenue,
            cogs_total,
            gross_profit,
            platform_fee_total,
            net_profit,
            profit_margin_percent,
            calculated_at
        )
        SELECT
            oh.id,
            oh.company_id,
            -- Revenue = Customer Paid + Platform Subsidy
            (COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) as total_rev,
            
            -- COGS
            COALESCE(items.cogs, 0) as total_cogs,
            
            -- Gross Profit
            (COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) - COALESCE(items.cogs, 0) as gross_prof,
            
            0 as fees, -- Placeholder
            
            -- Net Profit
            (COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) - COALESCE(items.cogs, 0) as net_prof,
            
            -- Margin %
            CASE WHEN (COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) > 0 THEN
                LEAST(9999.99, GREATEST(-9999.99,
                    ROUND(
                        (
                            ((COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) - COALESCE(items.cogs, 0)) 
                            / (COALESCE(oh.total_amount, 0) + COALESCE(oh.platform_discount_amount, 0)) 
                        ) * 100, 2
                    )
                ))
            ELSE 0 END as margin,
            
            NOW()
        FROM order_header oh
        LEFT JOIN (
            SELECT 
                oi.order_id, 
                SUM(oi.quantity * COALESCE(p.standard_cost, 0)) as cogs
            FROM order_item oi
            JOIN product p ON oi.product_id = p.id
            GROUP BY oi.order_id
        ) items ON oh.id = items.order_id
        ON CONFLICT (order_id) DO UPDATE SET
            total_revenue = EXCLUDED.total_revenue,
            cogs_total = EXCLUDED.cogs_total,
            gross_profit = EXCLUDED.gross_profit,
            net_profit = EXCLUDED.net_profit,
            profit_margin_percent = EXCLUDED.profit_margin_percent,
            calculated_at = NOW();
        """
        
        print("Executing Profit Calculation SQL (Upsert)...", flush=True)
        start_time = time.time()
        cur.execute(upsert_sql)
        row_count = cur.rowcount
        conn.commit()
        end_time = time.time()
        
        print(f"Profit Calculation Completed. Processed {row_count} orders in {end_time - start_time:.2f} seconds.", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("DB Connection closed.", flush=True)

if __name__ == "__main__":
    run_profit_calculation()
