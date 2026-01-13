
import requests
import json
from pprint import pprint

try:
    response = requests.get("http://localhost:9202/dashboard/stats")
    if response.status_code == 200:
        data = response.json()
        print("API Status: OK")
        if "platform_breakdown" in data:
            print(f"Platform Breakdown Count: {len(data['platform_breakdown'])}")
            for p in data['platform_breakdown']:
                print(f"\nPlatform: {p.get('platform')}")
                print(f"  - Count: {p.get('count')}")
                print(f"  - Revenue: {p.get('revenue')}")
                print(f"  - To Pack (paid_count): {p.get('paid_count')}")
                print(f"  - To Ship (packing_count): {p.get('packing_count')}")
        else:
            print("No platform_breakdown found in response")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Connection Error: {e}")
