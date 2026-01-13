import requests
import json
import time
import hashlib
import hmac

# Config
BASE_URL = "http://localhost:9202"
WEBHOOK_URL = f"{BASE_URL}/api/webhooks/tiktok"
APP_SECRET = "test_secret" # Mock secret, backend validation will fail signature but should still log/process if we bypass or if it's permissive
# Note: The current backend code logs a warning but CONTINUES if signature is invalid. 
# So we don't need the real secret to test the processing logic!

# Test Data (Real Order ID found from DB)
ORDER_ID = "579020012859655996"
SHOP_ID = "7495589412148152520" # Mock shop ID or fetch if needed, but let's try a realistic looking one or just 'unknown'

payload = {
    "type": "ORDER_STATUS_CHANGE",
    "shop_id": SHOP_ID,
    "timestamp": int(time.time()),
    "data": {
        "order_id": ORDER_ID,
        "order_status": "AWAITING_SHIPMENT", # Simulate status change
        "update_time": int(time.time())
    }
}

payload_bytes = json.dumps(payload).encode()
timestamp = str(int(time.time()))

# Generate Mock Signature
sign_string = f"{APP_SECRET}{timestamp}{payload_bytes.decode()}{APP_SECRET}"
signature = hmac.new(
    APP_SECRET.encode(),
    sign_string.encode(),
    hashlib.sha256
).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-TT-Signature": signature,
    "X-TT-Timestamp": timestamp,
}

print(f"Sending webhook to {WEBHOOK_URL}...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"\nResponse Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ Webhook sent successfully!")
        print("Check backend logs to confirm processing.")
    else:
        print("\n❌ Webhook failed!")

except Exception as e:
    print(f"\n❌ Error: {e}")
