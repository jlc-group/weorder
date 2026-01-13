
import asyncio
import httpx
import time
import hashlib
import hmac
import json
import os
import sys

# Standard setup for DB access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from app.core.database import SessionLocal
from app.models.order import OrderHeader

APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    s = f"{APP_SECRET}{path}{p}{body}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), s.encode(), hashlib.sha256).hexdigest()

async def run():
    print("Fetching data from TikTok...")
    async with httpx.AsyncClient(timeout=30.0) as c:
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts, "shop_id": SHOP_ID}
        # Get cipher again
        auth_p = {"app_key": APP_KEY, "timestamp": ts}
        auth_p["sign"] = sign("/authorization/202309/shops", auth_p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=auth_p, headers={"x-tts-access-token": ACCESS_TOKEN})
        cipher = next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)
        
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto = int(time.time())
        tfr = tto - (90 * 24 * 3600) # 90 days
        body_dict = {"page_size": 100, "request_time_from": tfr, "request_time_to": tto}
        body = json.dumps(body_dict, separators=(',', ':'))
        
        p = common.copy()
        p["sign"] = sign("/return_refund/202309/returns/search", p, body)
        p["access_token"] = ACCESS_TOKEN
        r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
        rets = r.json().get("data", {}).get("returns", [])
        
        db = SessionLocal()
        missing = []
        found = []
        for i in rets:
            oid = i['order_id']
            exists = db.query(OrderHeader).filter(OrderHeader.external_order_id == oid).first()
            if exists:
                found.append((oid, i['return_status'], exists.status_normalized))
            else:
                missing.append((oid, i['return_status']))
        
        print(f"API Returned {len(rets)} returns.")
        print(f"In DB: {len(found)}")
        print(f"Missing from DB: {len(missing)}")
        
        if missing:
            print("\nExample Missing IDs:")
            for m in missing[:10]:
                print(f"  - {m[0]} ({m[1]})")
        
        if found:
            print("\nExample Found IDs:")
            for f in found[:10]:
                print(f"  - {f[0]} ({f[1]}) | DB: {f[2]}")
        
        db.close()

if __name__ == "__main__":
    asyncio.run(run())
