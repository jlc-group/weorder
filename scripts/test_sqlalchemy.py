
print("Start import test...", flush=True)
try:
    import sqlalchemy
    print(f"SQLAlchemy version: {sqlalchemy.__version__}", flush=True)
    from sqlalchemy import create_engine
    print("create_engine imported", flush=True)
except Exception as e:
    print(f"Import failed: {e}", flush=True)
