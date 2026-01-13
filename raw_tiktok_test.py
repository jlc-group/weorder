
import asyncio
import httpx
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta

class TikTokTester:
    def __init__(self, app_key, app_secret, shop_id, access_token):
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_id = shop_id
        self.access_token = access_token
        self.shop_cipher = None
        self.BASE_URL = "https://open-api.tiktokglobalshop.com"

    def _generate_signature_v2(self, path, params, body=None):
        sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
        sorted_params = sorted(sign_params.items())
        params_string = "".join(f"{k}{v}" for k, v in sorted_params)
        body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
        sign_string = f"{self.app_secret}{path}{params_string}{body_str}{self.app_secret}"
        return hmac.new(self.app_secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

    async def fetch_shop_cipher(self):
        path = "/authorization/202309/shops"
        params = {"app_key": self.app_key, "timestamp": int(time.time())}
        params["sign"] = self._generate_signature_v2(path, params)
        async with httpx.AsyncClient() as client:
            headers = {"x-tts-access-token": self.access_token}
            resp = await client.get(f"{self.BASE_URL}{path}", params=params, headers=headers)
            data = resp.json()
            if data.get("code") == 0:
                for shop in data.get("data", {}).get("shops", []):
                    if str(shop.get("id")) == self.shop_id:
                        self.shop_cipher = shop.get("cipher")
                        print(f"Shop Cipher: {self.shop_cipher}")
                        return self.shop_cipher
        return None

    async def test_path(self, path, method="GET", body=None):
        if not self.shop_cipher:
            await self.fetch_shop_cipher()
        
        timestamp = int(time.time())
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.shop_id,
            "shop_cipher": self.shop_cipher
        }
        
        sign = self._generate_signature_v2(path, params, body)
        params["sign"] = sign
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json", 
                "x-tts-access-token": self.access_token
            }
            # Access token is usually in query params too for V2
            url_params = params.copy()
            url_params["access_token"] = self.access_token
            
            if method == "GET":
                resp = await client.get(f"{self.BASE_URL}{path}", params=url_params, headers=headers)
            else:
                resp = await client.post(f"{self.BASE_URL}{path}", params=url_params, json=body, headers=headers)
            
            print(f"\n--- TEST {method} {path} ---")
            print(f"Status: {resp.status_code}")
            try:
                data = resp.json()
                print(f"Code: {data.get('code')}")
                print(f"Msg: {data.get('message')}")
                if data.get('data'):
                    print(f"Data Keys: {list(data.get('data').keys())}")
                    # Look for items
                    for key in ['reverse_orders', 'reverse_list', 'reverse_order_list', 'returns']:
                        if key in data.get('data'):
                            items = data.get('data').get(key, [])
                            print(f"FOUND {key}: {len(items)} items")
                            if items: print(f"Sample: {items[0]}")
                else:
                    print(f"No Data: {data}")
            except:
                print(f"Raw Body: {resp.text[:500]}")

async def main():
    app_key = "6b8btm3gasnk7"
    app_secret = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
    shop_id = "7494581297305651553"
    access_token = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"
    
    tester = TikTokTester(app_key, app_secret, shop_id, access_token)
    
    # 1. Reverse Orders Search (Recommended V2)
    # Docs: POST /reverse/202309/reverse_orders/search
    await tester.test_path("/reverse/202309/reverse_orders/search", method="POST", body={})
    
    # 2. Reverse Orders List (Sometimes GET)
    await tester.test_path("/reverse/202309/reverse_orders", method="GET")

    # 3. Try with /return prefix just in case
    await tester.test_path("/return/202309/reverse_orders/search", method="POST", body={})

if __name__ == "__main__":
    asyncio.run(main())
