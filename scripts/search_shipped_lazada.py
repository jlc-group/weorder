
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

    async def get_orders(self, update_after, update_before):
        path = "/orders/get"
        # Note: Lazada /orders/get supports update_after/update_before in some versions,
        # but the standard one uses created_after. 
        # However, let's try to search by updated time if possible, 
        # or just fetch a large range of created orders and filter by updated_at.
        
        # Actually, let's fetch orders created in late Dec/early Jan and filter.
        created_after = "2025-12-25T00:00:00+00:00"
        created_before = "2026-01-10T00:00:00+00:00"
        
        params = {
            "app_key": self.key,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
            "access_token": self.token,
            "created_after": created_after,
            "created_before": created_before,
            "status": "shipped", # Filter by shipped to see when they were updated
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
    
    sl = SimpleLazada(key, secret, token)
    logger.info("Searching for Lazada orders created since Dec 25 with status 'shipped'...")
    try:
        res = await sl.get_orders(None, None)
        data = res.get('data', {})
        orders = data.get('orders', [])
        print(f"Total Shipped Orders found in range: {data.get('countTotal')}")
        
        # Check update times of the first few
        for o in orders[:5]:
            print(f"Order {o.get('order_id')} | Created: {o.get('created_at')} | Updated: {o.get('updated_at')}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
