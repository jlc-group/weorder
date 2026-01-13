
import asyncio
import httpx
import time
import hashlib
import hmac
import json

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

async def main():
    timestamp = int(time.time())
    path = "/order/202309/orders"
    order_id = "581932196284761716"
    
    # 1. Fetch shop cipher
    auth_path = "/authorization/202309/shops"
    auth_params = {"app_key": APP_KEY, "timestamp": timestamp}
    auth_params["sign"] = generate_signature(auth_path, auth_params)
    
    shop_cipher = ""
    async with httpx.AsyncClient() as client:
        headers = {"x-tts-access-token": ACCESS_TOKEN}
        resp = await client.get(f"{BASE_URL}{auth_path}", params=auth_params, headers=headers)
        data = resp.json()
        for shop in data.get("data", {}).get("shops", []):
            if str(shop.get("id")) == SHOP_ID:
                shop_cipher = shop.get("cipher")
                break
    
    params = {
        "app_key": APP_KEY,
        "timestamp": int(time.time()),
        "shop_id": SHOP_ID,
        "shop_cipher": shop_cipher,
        "ids": order_id
    }
    params["sign"] = generate_signature(path, params)
    params["access_token"] = ACCESS_TOKEN
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params, headers={"x-tts-access-token": ACCESS_TOKEN})
        print(resp.text)

if __name__ == "__main__":
    asyncio.run(main())
