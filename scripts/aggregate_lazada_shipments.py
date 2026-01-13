
import asyncio
import logging
import json
import sys
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
import httpx

logging.basicConfig(level=logging.ERROR, stream=sys.stdout)

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

    async def get_orders(self, created_after, created_before, cursor=None):
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
        if cursor: params["offset"] = cursor
        params["sign"] = self.sign(path, params)
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=20.0)
            return resp.json()

async def run():
    key = "129831"
    secret = "atPos8VYhnWAj17a6u2jKIxYBO8hAl9Y"
    token = "50000301715i4FlqbytGcfAv3mz1d5208a9ueIiRKxDvsGEZCQQDvr2TrC711k1K"
    sl = SimpleLazada(key, secret, token)
    
    # Check Jan 1-7
    created_after = "2026-01-01T00:00:00+00:00"
    created_before = "2026-01-07T23:59:59+00:00"
    
    date_counts = {}
    cursor = "0"
    
    print(f"Aggregating Lazada updated_at counts for orders created {created_after} to {created_before}")
    
    for _ in range(5): # Limit to 5 pages (500 orders) for speed
        res = await sl.get_orders(created_after, created_before, cursor)
        data = res.get('data', {})
        orders = data.get('orders', [])
        if not orders: break
        
        for o in orders:
            status = o.get('statuses', [''])[0]
            if status not in ['shipped', 'delivered', 'completed']: continue
            
            ua = o.get('updated_at', '')
            if ua:
                # Format: 2026-01-10 16:53:48 +0700
                date_str = ua.split(' ')[0]
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
        
        cursor = str(int(cursor) + len(orders))
        if len(orders) < 100: break

    print("Shipment/Delivery Events by Date (Lazada API):")
    for d in sorted(date_counts.keys()):
        print(f"{d}: {date_counts[d]}")

if __name__ == "__main__":
    asyncio.run(run())
