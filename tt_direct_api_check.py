import asyncio
import httpx
import time
import hashlib
import hmac
import json

APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    return hmac.new(APP_SECRET.encode(), f"{APP_SECRET}{path}{p}{body}{APP_SECRET}".encode(), hashlib.sha256).hexdigest()

async def run():
    print("=" * 60)
    print("DIRECT API QUERY TO TIKTOK (No DB involved)")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as c:
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts}
        p["sign"] = sign("/authorization/202309/shops", p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        cipher = next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)
        
        # 30 days
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto, tfr = int(time.time()), int(time.time()) - (30 * 24 * 3600)
        
        # Count all return types from API
        type_counts = {}
        total = 0
        physical_examples = []
        
        token = ""
        page = 0
        while page < 100:  # Limit to first 100 pages for quick scan
            page += 1
            body_dict = {"page_size": 50, "update_time_ge": tfr, "update_time_lt": tto}
            if token: body_dict["page_token"] = token
            body = json.dumps(body_dict, separators=(',', ':'))
            
            p = common.copy()
            p["sign"] = sign("/return_refund/202309/returns/search", p, body)
            p["access_token"] = ACCESS_TOKEN
            r = await c.post("https://open-api.tiktokglobalshop.com/return_refund/202309/returns/search", params=p, content=body, headers={"x-tts-access-token": ACCESS_TOKEN, "Content-Type": "application/json"})
            
            data = r.json().get("data")
            if not data:
                break
                
            returns = data.get("return_orders", [])
            
            for ret in returns:
                total += 1
                rt = ret.get("return_type", "UNKNOWN")
                type_counts[rt] = type_counts.get(rt, 0) + 1
                
                # Collect examples of physical returns
                if rt == "RETURN_AND_REFUND" and len(physical_examples) < 10:
                    physical_examples.append({
                        "order_id": ret.get("order_id"),
                        "status": ret.get("return_status"),
                        "reason": ret.get("return_reason_text", "")[:50],
                        "tracking": ret.get("return_tracking_number", "N/A")
                    })
            
            token = data.get("next_page_token")
            if not token:
                break
    
    print(f"\nTime Range: Last 30 days")
    print(f"Total Records from API: {total}")
    print(f"\n--- Return Type Distribution (FROM API DIRECTLY) ---")
    for k, v in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = (v/total*100) if total > 0 else 0
        label = "*** PHYSICAL RETURN ***" if k == "RETURN_AND_REFUND" else ""
        print(f"  {k}: {v} ({pct:.1f}%) {label}")
    
    print(f"\n--- Physical Return Examples (RETURN_AND_REFUND) ---")
    for i, ex in enumerate(physical_examples):
        print(f"  {i+1}. Order: {ex['order_id']}")
        print(f"     Status: {ex['status']}")
        print(f"     Tracking: {ex['tracking']}")
        print(f"     Reason: {ex['reason']}...")
        print()

if __name__ == "__main__":
    asyncio.run(run())
