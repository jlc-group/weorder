
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
    sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
    sorted_params = sorted(sign_params.items())
    params_string = "".join(f"{k}{v}" for k, v in sorted_params)
    body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
    sign_string = f"{APP_SECRET}{path}{params_string}{body_str}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

async def probe_endpoint(path, method="POST", params=None, body=None):
    timestamp = int(time.time())
    auth_path = "/authorization/202309/shops"
    auth_params = {"app_key": APP_KEY, "timestamp": timestamp}
    auth_params["sign"] = generate_signature(auth_path, auth_params)
    
    async with httpx.AsyncClient() as client:
        headers = {"x-tts-access-token": ACCESS_TOKEN}
        resp = await client.get(f"{BASE_URL}{auth_path}", params=auth_params, headers=headers)
        shop_cipher = next(s['cipher'] for s in resp.json()['data']['shops'] if str(s['id']) == SHOP_ID)
    
    combined_params = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": shop_cipher}
    if params: combined_params.update(params)
    combined_params["sign"] = generate_signature(path, combined_params, body)
    combined_params["access_token"] = ACCESS_TOKEN
    
    headers = {"Content-Type": "application/json", "x-tts-access-token": ACCESS_TOKEN}
    async with httpx.AsyncClient() as client:
        if method == "POST":
            resp = await client.post(f"{BASE_URL}{path}", params=combined_params, json=body, headers=headers)
        else:
            resp = await client.get(f"{BASE_URL}{path}", params=combined_params, headers=headers)
        return resp.json()

async def main():
    time_to = int(time.time())
    time_from = time_to - (60 * 24 * 3600)
    
    # Returns
    body = {"page_size": 20, "request_time_from": time_from, "request_time_to": time_to}
    data = await probe_endpoint("/return_refund/202309/returns/search", method="POST", body=body)
    returns = data.get("data", {}).get("returns", [])
    
    # Cancellations
    data2 = await probe_endpoint("/return_refund/202309/cancellations/search", method="POST", body=body)
    cancels = data2.get("data", {}).get("cancellations", [])
    
    print("REVERSE_ORDER_IDS")
    for r in returns:
        print(f"RETURN|{r.get('order_id')}|{r.get('return_status')}")
    for c in cancels:
        print(f"CANCEL|{c.get('order_id')}|{c.get('cancel_status')}")

if __name__ == "__main__":
    asyncio.run(main())
