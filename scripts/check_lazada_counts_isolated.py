
import asyncio
import logging
import json
import sys
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
import httpx

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("api_check")

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

    async def get_orders(self, created_after, created_before):
        path = "/orders/get"
        params = {
            "app_key": self.key,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
            "access_token": self.token,
            "created_after": created_after,
            "created_before": created_before,
            "limit": "100"
        }
        params["sign"] = self.sign(path, params)
        url = f"{self.base_url}{path}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            return resp.json()

async def run():
    # Jan 5 ICT = Jan 4 17:00 UTC - Jan 5 17:00 UTC
    # Lazada API likes ISO format with timezone
    created_after = "2026-01-04T17:00:00+00:00"
    created_before = "2026-01-05T17:00:00+00:00"
    
    key = "129831"
    secret = "atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y"
    token = "50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K"
    
    sl = SimpleLazada(key, secret, token)
    logger.info(f"Checking Lazada orders from {created_after} to {created_before}")
    try:
        res = await sl.get_orders(created_after, created_before)
        data = res.get('data', {})
        orders = data.get('orders', [])
        total = data.get('countTotal', len(orders))
        print(f"Total Orders in API: {total}")
        if orders:
            print(f"Sample Order Status: {orders[0].get('statuses')}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
