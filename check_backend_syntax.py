
import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import app.services.order_service...")
try:
    from app.services.order_service import OrderService
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
