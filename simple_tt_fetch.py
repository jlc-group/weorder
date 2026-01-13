
import asyncio
import httpx
import time
import hashlib
import hmac
import json

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
        # Shop cipher
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts}
        p["sign"] = sign("/authorization/202309/shops", p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        data = r.json()
        cipher = None
        for s in data.get('data', {}).get('shops', []):
            if str(s.get('id')) == SHOP_ID:
                cipher = s.get('cipher')
                break
        
        if not cipher:
            print("Cipher not found")
            return
            
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto = int(time.time())
        tfr = tto - (60 * 24 * 3600)
        body_dict = {"page_size": 20, "request_time_from": tfr, "request_time_to": tto}
        body = json.dumps(body_dict, separators=(',', ':'))
        
        # Returns
        p = common.copy()
        p["sign"] = sign("/return_refund/202309/returns/search", p, body)
        p["access_token"] = ACCESS_TOKEN
        r1 = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
        
        # Cancels
        p = common.copy()
        p["sign"] = sign("/return_refund/202309/cancellations/search", p, body)
        p["access_token"] = ACCESS_TOKEN
        r2 = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/cancellations/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
        
        rets = r1.json().get("data", {}).get("returns", [])
        cans = r2.json().get("data", {}).get("cancellations", [])
        
        print(f"RESULTS_START")
        for i in rets:
            print(f"RETURN|{i['order_id']}|{i['return_status']}")
        for i in cans:
            print(f"CANCEL|{i['order_id']}|{i['cancel_status']}")
        print(f"RESULTS_END")

if __name__ == "__main__":
    asyncio.run(run())
