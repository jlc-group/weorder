"""
Script to sync missing TikTok orders that are in Return API but not in order_header table.
This will:
1. Get order IDs from Return API (not_received orders)
2. Fetch full order details from TikTok Order API
3. Insert them into order_header table
4. Set status to DELIVERY_FAILED
"""
import asyncio
import httpx
import time
import hashlib
import hmac
import json
import psycopg2
from datetime import datetime

DB_CONFIG = {"host": "localhost", "user": "chanack", "dbname": "weorder", "port": 5432}
APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    return hmac.new(APP_SECRET.encode(), f"{APP_SECRET}{path}{p}{body}{APP_SECRET}".encode(), hashlib.sha256).hexdigest()

async def get_shop_cipher(c):
    ts = int(time.time())
    p = {"app_key": APP_KEY, "timestamp": ts}
    p["sign"] = sign("/authorization/202309/shops", p)
    r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
    return next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)

async def get_order_details(c, cipher, order_id):
    """Fetch order details from TikTok Order API"""
    common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
    p = common.copy()
    p["sign"] = sign(f"/order/202309/orders/{order_id}", p)
    p["access_token"] = ACCESS_TOKEN
    
    try:
        r = await c.get(f"https://open-api.tiktokglobalshop.com/order/202309/orders/{order_id}", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        data = r.json().get("data", {})
        return data
    except Exception as e:
        print(f"Error fetching order {order_id}: {e}")
        return None

async def run():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Get existing order IDs
    cur.execute("SELECT external_order_id FROM order_header WHERE channel_code = 'tiktok'")
    existing_ids = set(row[0] for row in cur.fetchall())
    print(f"Existing TikTok orders in DB: {len(existing_ids)}")
    
    # Collect all not_received order IDs from Return API
    missing_orders = set()
    
    print("\n=== Collecting not_received order IDs from Return API ===")
    
    async with httpx.AsyncClient(timeout=30.0) as c:
        cipher = await get_shop_cipher(c)
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto, tfr = int(time.time()), int(time.time()) - (90 * 24 * 3600)
        
        token = ""
        page = 0
        while True:
            page += 1
            body_dict = {"page_size": 50, "update_time_ge": tfr, "update_time_lt": tto}
            if token: body_dict["page_token"] = token
            body = json.dumps(body_dict, separators=(',', ':'))
            
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/returns/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            
            data = r.json().get("data")
            if not data:
                break
                
            returns = data.get("return_orders", [])
            
            for ret in returns:
                oid = ret.get("order_id")
                return_reason = ret.get("return_reason", "")
                if "not_received" in return_reason and oid not in existing_ids:
                    missing_orders.add(oid)
            
            if page % 50 == 0:
                print(f"  Page {page}... ({len(missing_orders)} missing orders found)")
            
            token = data.get("next_page_token")
            if not token:
                break
        
        print(f"\nTotal missing not_received orders: {len(missing_orders)}")
        
        if len(missing_orders) == 0:
            print("No missing orders to sync!")
            conn.close()
            return
        
        # Fetch and insert missing orders
        print(f"\n=== Fetching {len(missing_orders)} orders from Order API ===")
        inserted = 0
        
        for i, oid in enumerate(list(missing_orders)[:100]):  # Limit to first 100 for safety
            order = await get_order_details(c, cipher, oid)
            
            if order:
                try:
                    order_id = order.get("order_id", oid)
                    create_time = order.get("create_time")
                    update_time = order.get("update_time")
                    
                    # Get config ID for TikTok
                    cur.execute("SELECT id FROM platform_config WHERE platform = 'tiktok' LIMIT 1")
                    config_row = cur.fetchone()
                    config_id = config_row[0] if config_row else 1
                    
                    # Insert order
                    cur.execute("""
                        INSERT INTO order_header (
                            external_order_id, channel_code, platform_config_id,
                            status_raw, status_normalized, 
                            order_total, currency,
                            created_at, order_date, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (external_order_id) DO NOTHING
                    """, (
                        order_id, 'tiktok', config_id,
                        'REVERSE_not_received', 'DELIVERY_FAILED',
                        0, 'THB',
                        datetime.fromtimestamp(create_time) if create_time else datetime.now(),
                        datetime.fromtimestamp(create_time) if create_time else datetime.now()
                    ))
                    
                    if cur.rowcount > 0:
                        inserted += 1
                        
                except Exception as e:
                    print(f"Error inserting order {oid}: {e}")
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i+1}/{len(missing_orders)}... (inserted: {inserted})")
                conn.commit()
        
        conn.commit()
    
    # Final count
    cur.execute("SELECT count(*) FROM order_header WHERE channel_code = 'tiktok' AND status_normalized = 'DELIVERY_FAILED'")
    df_count = cur.fetchone()[0]
    
    print(f"\n=== COMPLETE ===")
    print(f"Inserted: {inserted}")
    print(f"Final DELIVERY_FAILED count: {df_count}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(run())
