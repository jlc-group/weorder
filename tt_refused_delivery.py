import asyncio
import httpx
import time
import hashlib
import hmac
import json
import psycopg2

DB_CONFIG = {"host": "localhost", "user": "chanack", "dbname": "weorder", "port": 5432}
APP_KEY = "6b8btm3gasnk7"
APP_SECRET = "9316fc54ec63e58fe2d2334906fb7f02b0a0b1a0"
SHOP_ID = "7494581297305651553"
ACCESS_TOKEN = "ROW_MHamBAAAAABL-b4cfjWufdkd83gygAZKmgdACkj5x8vtcTBflVKtU2Kv485T-uYbjGo5lDv9X0OP4_bkt-Goh-YgaReAy14tl-9O20P3Ocl3Bb2-giI1DOirWYJ4ItIR95JNil4LAojvPlzEZo1F62S6ryKQAhaR1h5b6UNBI67BmsLWLgP9gg"

def sign(path, params, body=""):
    p = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    return hmac.new(APP_SECRET.encode(), f"{APP_SECRET}{path}{p}{body}{APP_SECRET}".encode(), hashlib.sha256).hexdigest()

async def run():
    print("=" * 70)
    print("TikTok Return Analysis - Looking for 'Customer Refused Delivery'")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as c:
        ts = int(time.time())
        p = {"app_key": APP_KEY, "timestamp": ts}
        p["sign"] = sign("/authorization/202309/shops", p)
        r = await c.get("https://open-api.tiktokglobalshop.com/authorization/202309/shops", params=p, headers={"x-tts-access-token": ACCESS_TOKEN})
        cipher = next(s['cipher'] for s in r.json()['data']['shops'] if str(s['id']) == SHOP_ID)
        
        common = {"app_key": APP_KEY, "timestamp": int(time.time()), "shop_id": SHOP_ID, "shop_cipher": cipher}
        tto, tfr = int(time.time()), int(time.time()) - (30 * 24 * 3600)
        
        # Collect all unique return_reason and return_reason_text
        reasons = {}
        refuse_delivery = []
        
        token = ""
        page = 0
        while page < 50:  # First 50 pages
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
                reason = ret.get("return_reason", "UNKNOWN")
                reason_text = ret.get("return_reason_text", "")
                return_type = ret.get("return_type", "")
                order_id = ret.get("order_id")
                
                key = f"{reason}|{reason_text[:50]}"
                if key not in reasons:
                    reasons[key] = {"count": 0, "reason": reason, "text": reason_text, "type": return_type}
                reasons[key]["count"] += 1
                
                # Check for "refused delivery" keywords
                if any(kw in reason_text.lower() for kw in ["not receive", "did not receive", "refused", "not accepted", "ไม่รับ", "ปฏิเสธ"]):
                    if len(refuse_delivery) < 10:
                        refuse_delivery.append({
                            "order_id": order_id,
                            "reason": reason,
                            "reason_text": reason_text,
                            "type": return_type
                        })
            
            token = data.get("next_page_token")
            if not token:
                break
    
    print("\n--- All Return Reasons (sorted by count) ---")
    for key, val in sorted(reasons.items(), key=lambda x: -x[1]["count"])[:20]:
        print(f"  [{val['count']}] {val['reason']}")
        print(f"      Text: {val['text'][:60]}...")
        print(f"      Type: {val['type']}")
        print()
    
    print("\n--- Orders with 'Refused/Not Receive' keywords ---")
    print(f"Found: {len(refuse_delivery)}")
    for item in refuse_delivery:
        print(f"  Order: {item['order_id']}")
        print(f"    Reason: {item['reason_text']}")
        print(f"    Type: {item['type']}")
        print()

    # Also check DB for any status that might indicate refused delivery
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT status_raw, count(*) 
        FROM order_header 
        WHERE channel_code = 'tiktok' 
          AND (status_raw ILIKE '%refuse%' OR status_raw ILIKE '%fail%' OR status_raw ILIKE '%return%')
        GROUP BY status_raw 
        ORDER BY count DESC 
        LIMIT 20
    """)
    db_statuses = cur.fetchall()
    
    print("\n--- DB Status containing 'refuse/fail/return' ---")
    for row in db_statuses:
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(run())
