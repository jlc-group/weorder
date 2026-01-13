import asyncio
import httpx
import time
import hashlib
import hmac
import json
import psycopg2

DB_CONFIG = {"host": "localhost", "user": "chanack", "dbname": "weorder", "port": 5432}
APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    return hmac.new(APP_SECRET.encode(), f"{APP_SECRET}{path}{p}{body}{APP_SECRET}".encode(), hashlib.sha256).hexdigest()

async def run():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    stats = {"found": 0, "updated": 0}
    unique_ids = set()
    
    print("=" * 60)
    print("FORCE UPDATE: All not_received orders -> DELIVERY_FAILED")
    print("(Ignoring current status)")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as c:
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts}
        p["sign"] = sign("/authorization/202309/shops", p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        cipher = next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)
        
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto, tfr = int(time.time()), int(time.time()) - (180 * 24 * 3600)  # 180 days
        
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
                return_status = ret.get("return_status", "UNKNOWN")
                
                # Check for not_received AND skip duplicates
                if "not_received" in return_reason and oid not in unique_ids:
                    unique_ids.add(oid)
                    stats["found"] += 1
                    
                    # Force update to DELIVERY_FAILED (ignore current status)
                    cur.execute(
                        "UPDATE order_header SET status_normalized = 'DELIVERY_FAILED', status_raw = %s, updated_at = NOW() "
                        "WHERE external_order_id = %s",
                        (f"REVERSE_{return_status}", oid)
                    )
                    if cur.rowcount > 0:
                        stats["updated"] += 1
            
            if page % 50 == 0:
                print(f"  Page {page}... (unique not_received: {stats['found']}, updated: {stats['updated']})")
                conn.commit()
            
            token = data.get("next_page_token")
            if not token:
                break
    
    conn.commit()
    
    # Final counts
    cur.execute("SELECT count(*) FROM order_header WHERE channel_code = 'tiktok' AND status_normalized = 'DELIVERY_FAILED'")
    df_count = cur.fetchone()[0]
    
    print(f"\n=== COMPLETE ===")
    print(f"Unique not_received orders: {stats['found']}")
    print(f"Updated to DELIVERY_FAILED: {stats['updated']}")
    print(f"\nFinal TikTok DELIVERY_FAILED count: {df_count}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(run())
