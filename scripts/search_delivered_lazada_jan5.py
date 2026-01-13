
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

    async def get_orders(self, created_after, created_before, status):
        path = "/orders/get"
        params = {
            "app_key": self.key,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
            "access_token": self.token,
            "created_after": created_after,
            "created_before": created_before,
            "status": status,
            "limit": "100"
        }
        params["sign"] = self.sign(path, params)
        url = f"{self.base_url}{path}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=15.0)
            return resp.json()

async def run():
    key = "129831"
    secret = "atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y"
    token = "50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K"
    
    # Check orders created Jan 1-7
    created_after = "2026-01-01T00:00:00+00:00"
    created_before = "2026-01-07T23:59:59+00:00"
    
    sl = SimpleLazada(key, secret, token)
    logger.info(f"Searching for Lazada orders created {created_after} to {created_before} with status 'delivered'...")
    try:
        res = await sl.get_orders(created_after, created_before, "delivered")
        data = res.get('data', {})
        orders = data.get('orders', [])
        print(f"Total Delivered Orders found: {data.get('countTotal')}")
        
        jan5_hits = 0
        for o in orders:
            ua = o.get('updated_at', '')
            if '2026-01-05' in ua or '2026-01-06' in ua: # Check Jan 5/6
                jan5_hits += 1
                if jan5_hits <= 5:
                    print(f"Order {o.get('order_id')} | Created: {o.get('created_at')} | Updated: {o.get('updated_at')}")
        
        print(f"Orders with updated_at on Jan 5/6 (ICT) in this page: {jan5_hits}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
