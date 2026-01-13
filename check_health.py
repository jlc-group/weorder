
import requests
import sys

try:
    print("Checking /health...")
    resp = requests.get("http://localhost:9202/health", timeout=5)
    print(f"Health Status: {resp.status_code}")
    print(resp.json())
except Exception as e:
    print(f"Health Check Failed: {e}")
    sys.exit(1)
