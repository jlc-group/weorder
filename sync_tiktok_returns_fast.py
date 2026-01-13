
import asyncio
import httpx
import time
import hashlib
import hmac
import json
import psycopg2
from datetime import datetime, timedelta

# Config from app/core/config.py
DB_CONFIG = {
    "host": "localhost",
    "user": "chanack",
    "dbname": "weorder",
    "port": 5432
}

# TikTok Credentials
APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    s = f"{APP_SECRET}{path}{p}{body}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), s.encode(), hashlib.sha256).hexdigest()

async def get_cipher(client):
    ts = int(time.time())
    p = {"app_key": APP_KEY, "timestamp": ts}
    p["sign"] = sign("/authorization/202309/shops", p)
    r = await client.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
    data = r.json()
    for s in data['data']['shops']:
        if str(s['id']) == SHOP_ID:
            return s['cipher']
    return None

async def run():
    print("Starting Fast TikTok Returns Sync (90 days)...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        cipher = await get_cipher(client)
        if not cipher:
            print("Cipher not found!")
            return
            
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto = int(time.time())
        tfr = tto - (90 * 24 * 3600)
        
        # 1. Fetch Returns
        print("Fetching returns...")
        token = ""
        total_rets = 0
        updated_rets = 0
        while True:
            body_dict = {"page_size": 20, "update_time_ge": tfr, "update_time_lt": tto}
            if token: body_dict["page_token"] = token
            body = json.dumps(body_dict, separators=(',', ':'))
            
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/returns/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await client.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            data = r.json().get("data", {})
            returns = data.get("returns", [])
            
            for i in returns:
                oid = i['order_id']
                status = i['return_status']
                total_rets += 1
                
                # Check if exists
                cur.execute("SELECT status_normalized FROM order_header WHERE external_order_id = %s", (oid,))
                row = cur.fetchone()
                if not row:
                    # Optional: print(f"  [RETURN] Skip {oid} - NOT IN DB")
                    pass
                elif row[0] in ('RETURNED', 'CANCELLED'):
                    pass
                else:
                    # Update DB
                    cur.execute(
                        "UPDATE order_header SET status_normalized = %s, status_raw = %s, updated_at = NOW() "
                        "WHERE external_order_id = %s",
                        ('RETURNED', f"REVERSE_{status}", oid)
                    )
                    if cur.rowcount > 0:
                        updated_rets += 1
                        print(f"  [RETURN] Updated {oid} from {row[0]} to {status}")
            
            token = data.get("next_page_token")
            if not token: break
            print(f"  Moving to next page (token: {token[:10]}...)")
            
        print(f"Returns Summary: Fetched {total_rets}, Updated {updated_rets}")

        # 2. Fetch Cancellations
        print("\nFetching cancellations...")
        token = ""
        total_cans = 0
        updated_cans = 0
        while True:
            body_dict = {"page_size": 20, "update_time_ge": tfr, "update_time_lt": tto}
            if token: body_dict["page_token"] = token
            body = json.dumps(body_dict, separators=(',', ':'))
            
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/cancellations/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await client.post("https://open-api.tiktokglobalshop.com/return_refund/202309/cancellations/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            data = r.json().get("data", {})
            cancels = data.get("cancellations", [])
            
            for i in cancels:
                oid = i['order_id']
                status = i['cancel_status']
                total_cans += 1
                
                # Update DB
                cur.execute(
                    "UPDATE order_header SET status_normalized = %s, status_raw = %s, updated_at = NOW() "
                    "WHERE external_order_id = %s AND channel_code = 'tiktok' AND status_normalized NOT IN ('RETURNED', 'CANCELLED')",
                    ('CANCELLED', f"REVERSE_{status}", oid)
                )
                if cur.rowcount > 0:
                    updated_cans += 1
                    print(f"  [CANCEL] Updated {oid} to {status}")
            
            token = data.get("next_page_token")
            if not token: break
            print(f"  Moving to next page (token: {token[:10]}...)")
            
        print(f"Cancellations Summary: Fetched {total_cans}, Updated {updated_cans}")
        
    conn.commit()
    cur.close()
    conn.close()
    print("Sync Complete.")

if __name__ == "__main__":
    asyncio.run(run())
