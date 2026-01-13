
import requests
import json
import uuid

# Config
BASE_URL = "http://localhost:9202/api/prepack"
WAREHOUSE_ID = "baafef76-4094-4a7f-ad2d-f3c9ef95b2a0" 
PRODUCT_ID = "993256f0-3e10-42e2-9087-d5e8008f8e05"

def test_create_batch():
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "box_count": 3,
        "items": [
            {
                "product_id": PRODUCT_ID,
                "sku": "TEST-SKU-001",
                "quantity": 2
            }
        ]
    }
    
    print("\n--- Testing Create Batch ---")
    try:
        response = requests.post(f"{BASE_URL}/batch/create", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_list_boxes():
    print("\n--- Testing List Boxes ---")
    try:
        response = requests.get(f"{BASE_URL}/list")
        if response.status_code == 200:
            print(f"Status: 200 OK")
            print(f"Boxes found: {response.json().get('count')}")
            # print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_create_batch()
    test_list_boxes()
