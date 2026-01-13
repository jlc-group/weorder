
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

BASE_URLS = [
    "https://open-api.tiktokglobalshop.com",
    "https://open-api.tiktokshop.com"
]

def generate_signature(path, params, body=None):
    # Sort params
    sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
    sorted_params = sorted(sign_params.items())
    params_string = "".join(f"{k}{v}" for k, v in sorted_params)
    
    body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
    sign_string = f"{APP_SECRET}{path}{params_string}{body_str}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

async def probe_endpoint(base_url, path, method="POST", body=None):
    timestamp = int(time.time())
    
    # Fetch shop cipher (using the specific base URL)
    auth_path = "/authorization/202309/shops"
    auth_params = {"app_key": APP_KEY, "timestamp": timestamp}
    auth_params["sign"] = generate_signature(auth_path, auth_params)
    
    shop_cipher = ""
    async with httpx.AsyncClient() as client:
        headers = {"x-tts-access-token": ACCESS_TOKEN}
        try:
            resp = await client.get(f"{base_url}{auth_path}", params=auth_params, headers=headers)
            data = resp.json()
            if data.get("code") == 0:
                for shop in data.get("data", {}).get("shops", []):
                    if str(shop.get("id")) == SHOP_ID:
                        shop_cipher = shop.get("cipher")
                        break
        except Exception as e:
            print(f"Error fetching cipher from {base_url}: {e}")
            return

    # Probe
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
    
    print(f"Probing {base_url}{path} ...")
    async with httpx.AsyncClient() as client:
        try:
            if method == "POST":
                resp = await client.post(f"{base_url}{path}", params=params, json=body, headers=headers)
            else:
                resp = await client.get(f"{base_url}{path}", params=params, headers=headers)
            
            print(f"Status: {resp.status_code}")
            try:
                res_data = resp.json()
                print(f"Response: {res_data}")
            except:
                print(f"Raw: {resp.text[:200]}")
        except Exception as e:
            print(f"Error for {base_url}{path}: {e}")

async def main():
    path = "/reverse/202309/reverse_orders/search"
    for base in BASE_URLS:
        await probe_endpoint(base, path, method="POST", body={"page_size": 10})
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(main())
