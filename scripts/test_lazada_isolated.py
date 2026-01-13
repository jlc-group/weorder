
import asyncio
import logging
import json
import sys
import hashlib
import hmac
import time
from datetime import datetime, timedelta
import httpx

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("api_isolated")

class SimpleLazada:
    def __init__(self, key, secret, token):
        self.key = key
        self.secret = secret
        self.token = token
        self.base_url = "https://api.lazada.co.th/rest"

    def sign(self, path, params):
        sorted_params = sorted(params.items())
        sign_string = path
        for k, v in sorted_params:
            sign_string += f"{k}{v}"
        return hmac.new(self.secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest().upper()

    async def get_order(self, order_id):
        path = "/order/get"
        params = {
            "app_key": self.key,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
            "access_token": self.token,
            "order_id": order_id
        }
        params["sign"] = self.sign(path, params)
        url = f"{self.base_url}{path}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            return resp.json()

async def run():
    key = "129831"
    secret = "atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y"
    token = "50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K"
    
    # ID which is currently 'NEW' in our DB but was created on Jan 5
    order_id = "1074144794996468"
    
    sl = SimpleLazada(key, secret, token)
    logger.info(f"Targeting order {order_id}...")
    try:
        res = await sl.get_order(order_id)
        print(json.dumps(res, indent=2))
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
