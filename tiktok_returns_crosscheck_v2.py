
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

APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    s = f"{APP_SECRET}{path}{p}{body}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), s.encode(), hashlib.sha256).hexdigest()

async def run():
    print("DEBUG: Starting run...")
    try:
        from app.core.database import SessionLocal
        from app.models.order import OrderHeader
        print("DEBUG: DB imports successful")
    except Exception as e:
        print(f"DEBUG: DB imports failed: {e}")
        return

    async with httpx.AsyncClient(timeout=30.0) as c:
        try:
            ts = int(time.time())
            p = {"app_key": APP_KEY, "timestamp": ts}
            p["sign"] = sign("/authorization/202309/shops", p)
            print("DEBUG: Fetching shop cipher...")
            r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
            data = r.json()
            if data.get("code") != 0:
                print(f"DEBUG: Shop API Error: {data}")
                return
            
            cipher = None
            for s in data.get('data', {}).get('shops', []):
                if str(s.get('id')) == SHOP_ID:
                    cipher = s.get('cipher')
                    break
            
            if not cipher:
                print("DEBUG: Cipher not found for shop")
                return
            print(f"DEBUG: Cipher found: {cipher[:10]}...")
            
            common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
            tto = int(time.time())
            tfr = tto - (60 * 24 * 3600)
            body_dict = {"page_size": 20, "request_time_from": tfr, "request_time_to": tto}
            body = json.dumps(body_dict, separators=(',', ':'))
            
            print("DEBUG: Fetching returns...")
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/returns/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            returns_data = r.json()
            
            print("DEBUG: Fetching cancellations...")
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/cancellations/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/cancellations/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            cancels_data = r.json()
            
        except Exception as e:
            print(f"DEBUG: API Error: {e}")
            return

    try:
        db = SessionLocal()
        print(f"\n{'Type':<10} | {'Order ID':<20} | {'Tiktok Status':<35} | {'DB Status'}")
        print("-" * 85)
        
        for i in returns_data.get("data", {}).get("returns", []):
            order_id = i['order_id']
            status = i['return_status']
            order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
            db_status = order.status_normalized if order else "NOT_IN_DB"
            print(f"RETURN     | {order_id:<20} | {status:<35} | {db_status}")

        for i in cancels_data.get("data", {}).get("cancellations", []):
            order_id = i['order_id']
            status = i['cancel_status']
            order = db.query(OrderHeader).filter(OrderHeader.external_order_id == order_id).first()
            db_status = order.status_normalized if order else "NOT_IN_DB"
            print(f"CANCEL     | {order_id:<20} | {status:<35} | {db_status}")
            
        db.close()
    except Exception as e:
        print(f"DEBUG: Final processing error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
