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
    
    print("=" * 60)
    print("Checking if Physical Return order_ids exist in DB")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as c:
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts}
        p["sign"] = sign("/authorization/202309/shops", p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        cipher = next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)
        
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto, tfr = int(time.time()), int(time.time()) - (30 * 24 * 3600)
        
        # Just check firs 50 physical returns
        body_dict = {"page_size": 50, "update_time_ge": tfr, "update_time_lt": tto}
        body = json.dumps(body_dict, separators=(',', ':'))
        
        p = common.copy()
        p["sign"] = sign("/return_refund/202309/returns/search", p, body)
        p["access_token"] = ACCESS_TOKEN
        r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
        
        data = r.json().get("data", {})
        returns = data.get("return_orders", [])
        
        in_db = 0
        not_in_db = 0
        examples_not_in_db = []
        
        for ret in returns:
            oid = ret.get("order_id")
            return_type = ret.get("return_type", "UNKNOWN")
            
            if return_type == "RETURN_AND_REFUND":
                cur.execute("SELECT id FROM order_header WHERE external_order_id = %s", (oid,))
                row = cur.fetchone()
                if row:
                    in_db += 1
                else:
                    not_in_db += 1
                    if len(examples_not_in_db) < 5:
                        examples_not_in_db.append(oid)
        
        print(f"\nChecked first 50 RETURN_AND_REFUND records:")
        print(f"  In DB: {in_db}")
        print(f"  NOT in DB: {not_in_db}")
        
        if examples_not_in_db:
            print(f"\nExample order_ids NOT in DB:")
            for oid in examples_not_in_db:
                print(f"  - {oid}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(run())
