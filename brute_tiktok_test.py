
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
        self.shop_cipher = "ROW_Mfxq0QAAAADY9jhQTMr4JXq4U19IpM5-"
        self.BASE_URL = "https://open-api.tiktokglobalshop.com"

    def _generate_signature_v2(self, path, params, body=None):
        sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
        sorted_params = sorted(sign_params.items())
        params_string = "".join(f"{k}{v}" for k, v in sorted_params)
        body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
        sign_string = f"{self.app_secret}{path}{params_string}{body_str}{self.app_secret}"
        return hmac.new(self.app_secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

    async def test_path(self, path, method="POST", body=None):
        timestamp = int(time.time())
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.shop_id,
            "shop_cipher": self.shop_cipher
        }
        
        sign = self._generate_signature_v2(path, params, body)
        params["sign"] = sign
        params["access_token"] = self.access_token
        
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "x-tts-access-token": self.access_token}
            if method == "GET":
                resp = await client.get(f"{self.BASE_URL}{path}", params=params, headers=headers)
            else:
                resp = await client.post(f"{self.BASE_URL}{path}", params=params, json=body, headers=headers)
            
            print(f"[{resp.status_code}] {method} {path} -> {resp.text[:150]}")

async def main():
    app_key = "6b8btm3gasnk7"
    app_secret = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
    shop_id = "7494581297305651553"
    access_token = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"
    
    tester = TikTokTester(app_key, app_secret, shop_id, access_token)
    
    paths = [
        ("/reverse/202309/reverse_orders/search", "POST"),
        ("/order/202309/reverse_orders/search", "POST"),
        ("/fulfillment/202309/reverse_orders/search", "POST"),
        ("/return/202309/returns/search", "POST"),
    ]
    for p in paths:
        await tester.test_path(p[0], p[1], body={})

if __name__ == "__main__":
    asyncio.run(main())
