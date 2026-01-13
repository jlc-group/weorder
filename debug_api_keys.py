
import requests
import json

try:
    response = requests.get("http://localhost:9202/api/dashboard/stats")
    if response.status_code == 200:
        data = response.json()
        print("Full Data:", data)
        if "platform_breakdown" in data:
            print("platform_breakdown is present.")
            print("Value:", data["platform_breakdown"])
        else:
            print("platform_breakdown is MISSING.")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Connection Error: {e}")
