
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

BATCH_SIZE = 5000

def backfill_order_header():
    """Backfill new order_header columns from raw_payload"""
    print("Starting Order Header Backfill...", flush=True)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Single efficient UPDATE for all order_header columns
    update_sql = """
    UPDATE order_header oh SET
        rts_time = CASE 
            WHEN (raw_payload->>'rts_time') IS NOT NULL AND (raw_payload->>'rts_time')::bigint > 0
            THEN to_timestamp((raw_payload->>'rts_time')::bigint)
            ELSE NULL END,
        paid_time = CASE 
            WHEN (raw_payload->>'paid_time') IS NOT NULL AND (raw_payload->>'paid_time')::bigint > 0
            THEN to_timestamp((raw_payload->>'paid_time')::bigint)
            ELSE NULL END,
        delivery_time = CASE 
            WHEN (raw_payload->>'delivery_time') IS NOT NULL AND (raw_payload->>'delivery_time')::bigint > 0
            THEN to_timestamp((raw_payload->>'delivery_time')::bigint)
            ELSE NULL END,
        collection_time = CASE 
            WHEN (raw_payload->>'collection_time') IS NOT NULL AND (raw_payload->>'collection_time')::bigint > 0
            THEN to_timestamp((raw_payload->>'collection_time')::bigint)
            ELSE NULL END,
        original_shipping_fee = COALESCE((raw_payload->'payment'->>'original_shipping_fee')::numeric, 0),
        shipping_fee_platform_discount = COALESCE((raw_payload->'payment'->>'shipping_fee_platform_discount')::numeric, 0),
        is_cod = COALESCE((raw_payload->>'is_cod')::boolean, FALSE),
        courier_code = COALESCE(oh.courier_code, raw_payload->>'shipping_provider'),
        payment_method = COALESCE(oh.payment_method, raw_payload->>'payment_method_name')
    WHERE raw_payload IS NOT NULL
    AND channel_code = 'tiktok'
    AND (rts_time IS NULL OR paid_time IS NULL);
    """
    
    print("Executing backfill for order_header (timestamps, shipping, COD)...", flush=True)
    start = time.time()
    cur.execute(update_sql)
    count = cur.rowcount
    conn.commit()
    print(f"Updated {count} order_header records in {time.time() - start:.2f}s", flush=True)
    
    conn.close()

def backfill_order_item():
    """Backfill new order_item columns from raw_payload (via JOIN)"""
    print("\nStarting Order Item Backfill...", flush=True)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Complex UPDATE: Join order_item with order_header's raw_payload line_items
    update_sql = """
    UPDATE order_item oi SET
        original_price = COALESCE((item_data->>'original_price')::numeric, 0),
        platform_discount = COALESCE((item_data->>'platform_discount')::numeric, 0),
        seller_discount = COALESCE((item_data->>'seller_discount')::numeric, 0)
    FROM (
        SELECT 
            oh.id as order_id,
            elem->>'seller_sku' as sku,
            elem as item_data
        FROM order_header oh,
             jsonb_array_elements(oh.raw_payload->'line_items') elem
        WHERE oh.raw_payload IS NOT NULL
        AND oh.channel_code = 'tiktok'
    ) as items
    WHERE oi.order_id = items.order_id
    AND oi.sku = items.sku
    AND oi.original_price IS NULL;
    """
    
    print("Executing backfill for order_item (original_price, discounts)...", flush=True)
    start = time.time()
    cur.execute(update_sql)
    count = cur.rowcount
    conn.commit()
    print(f"Updated {count} order_item records in {time.time() - start:.2f}s", flush=True)
    
    conn.close()

if __name__ == "__main__":
    backfill_order_header()
    backfill_order_item()
    print("\n✅ All backfills complete!", flush=True)
