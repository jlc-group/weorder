
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

print("Starting import test...", flush=True)
sys.path.append(os.getcwd())

try:
    print("Importing settings...", flush=True)
    from app.core.config import settings
    print(f"Settings loaded: DB URL len={len(settings.DATABASE_URL)}", flush=True)
except Exception as e:
    print(f"Failed to import settings: {e}", flush=True)

try:
    print("Importing SessionLocal...", flush=True)
    from app.core.database import SessionLocal
    print("SessionLocal imported", flush=True)
    db = SessionLocal()
    print("Session created", flush=True)
    db.close()
    print("Session closed", flush=True)
except Exception as e:
    print(f"Failed to use DB: {e}", flush=True)
