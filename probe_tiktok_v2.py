
import asyncio
import httpx
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta

# TikTok Credentials
APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

BASE_URL = "https://open-api.tiktokglobalshop.com"

def generate_signature(path, params, body=None):
    # Sort params
    sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
    sorted_params = sorted(sign_params.items())
    params_string = "".join(f"{k}{v}" for k, v in sorted_params)
    
    body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
    sign_string = f"{APP_SECRET}{path}{params_string}{body_str}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

async def probe_endpoint(path, method="POST", body=None):
    timestamp = int(time.time())
    
    # Fetch shop cipher
    auth_path = "/authorization/202309/shops"
    auth_params = {"app_key": APP_KEY, "timestamp": timestamp}
    auth_params["sign"] = generate_signature(auth_path, auth_params)
    
    shop_cipher = ""
    async with httpx.AsyncClient() as client:
        headers = {"x-tts-access-token": ACCESS_TOKEN}
        resp = await client.get(f"{BASE_URL}{auth_path}", params=auth_params, headers=headers)
        data = resp.json()
        if data.get("code") == 0:
            for shop in data.get("data", {}).get("shops", []):
                if str(shop.get("id")) == SHOP_ID:
                    shop_cipher = shop.get("cipher")
                    break
    
    params = {
        "app_key": APP_KEY,
        "timestamp": int(time.time()),
        "shop_id": SHOP_ID,
    }
    if shop_cipher:
        params["shop_cipher"] = shop_cipher
    
    params["sign"] = generate_signature(path, params, body)
    params["access_token"] = ACCESS_TOKEN
    
    headers = {"Content-Type": "application/json", "x-tts-access-token": ACCESS_TOKEN}
    
    async with httpx.AsyncClient() as client:
        if method == "POST":
            resp = await client.post(f"{BASE_URL}{path}", params=params, json=body, headers=headers)
        else:
            resp = await client.get(f"{BASE_URL}{path}", params=params, headers=headers)
        
        data = resp.json()
        return data

async def main():
    print("=== Fetching Returns ===")
    returns_data = await probe_endpoint("/return_refund/202309/returns/search", method="POST", body={"page_size": 20})
    if returns_data.get("code") == 0:
        orders = returns_data.get("data", {}).get("return_orders", [])
        for o in orders:
            print(f"Return ID: {o.get('return_id')} | Status: {o.get('return_status')} | Order ID: {o.get('order_id')}")
    else:
        print(f"Error fetching returns: {returns_data}")

    print("\n=== Fetching Cancellations ===")
    cancel_data = await probe_endpoint("/return_refund/202309/cancellations/search", method="POST", body={"page_size": 20})
    if cancel_data.get("code") == 0:
        cancellations = cancel_data.get("data", {}).get("cancellations", [])
        for c in cancellations:
            print(f"Cancel ID: {c.get('cancel_id')} | Status: {c.get('cancel_status')} | Order ID: {c.get('order_id')}")
    else:
        print(f"Error fetching cancellations: {cancel_data}")

if __name__ == "__main__":
    asyncio.run(main())
