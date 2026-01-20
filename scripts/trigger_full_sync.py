import urllib.request
import urllib.parse
import json
import time

base_url = "http://localhost:9203/api"

def trigger_post(endpoint, params=None):
    url = f"{base_url}{endpoint}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    
    print(f"Triggering {url}...")
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Success.")
                return json.loads(response.read().decode())
            else:
                print(f"Error {response.status}: {response.read().decode()}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    print("=== Starting Full Update (Orders & Finance) ===")

    # 1. Trigger Order Sync (Background)
    # This syncs last 30 days by default
    print("\n1. Triggering Order Sync (All Platforms)...")
    trigger_post("/sync/trigger")

    # 2. Trigger Finance Sync (Foreground/Wait)
    # Sync last 15 days to catch up (stale since Jan 8th)
    print("\n2. Triggering Finance Sync (Last 15 Days)...")
    
    platforms = ["shopee", "tiktok", "lazada"]
    
    for platform in platforms:
        print(f"  > Syncing {platform} finance...")
        # Note: Finance sync might take time as it waits for completion
        trigger_post(f"/finance/sync/{platform}", {"days": 15})
        time.sleep(1) # Gap

    print("\n=== Sync Triggered ===")
    print("Order sync is running in background.")
    print("Finance sync completed.")

if __name__ == "__main__":
    main()
