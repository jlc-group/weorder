
print("Start script...")
import sys
import os
print("Importing os/sys done")

sys.path.append(os.getcwd())
print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

try:
    print("Importing sqlalchemy...")
    from sqlalchemy import text
    print("Importing sqlalchemy done")
except Exception as e:
    print(f"Error importing sqlalchemy: {e}")

try:
    print("Importing app.core...")
    from app.core import SessionLocal
    print("Importing app.core done")
except Exception as e:
    print(f"Error importing app.core: {e}")

try:
    print("Importing app.models.order...")
    from app.models.order import OrderHeader
    print("Importing app.models.order done")
except Exception as e:
    print(f"Error importing app.models.order: {e}")

print("End script")
