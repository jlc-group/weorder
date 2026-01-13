
import requests
from datetime import date

# Config
BASE_URL = "http://localhost:9202/api/report"
TARGET_DATE = "2026-01-04"

def test_daily_outbound():
    print(f"\n--- Testing Daily Outbound Report for {TARGET_DATE} ---")
    try:
        response = requests.get(f"{BASE_URL}/daily-outbound", params={"target_date": TARGET_DATE})
        if response.status_code == 200:
            data = response.json()
            print(f"Status: 200 OK")
            print(f"Date: {data.get('date')}")
            print(f"Summary: {data.get('summary')}")
            if data.get('items'):
                print(f"Top Item: {data.get('items')[0]}")
            else:
                print("No items found.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_daily_outbound()
