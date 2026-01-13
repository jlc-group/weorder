
import sys
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
from app.core import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def inspect_shopee():
    print("--- Shopee Status Check ---")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT status_normalized, raw_payload->>'order_status' as raw_status, count(*) FROM order_header WHERE channel_code = 'shopee' AND status_normalized IN ('PAID', 'READY_TO_SHIP', 'PACKING') GROUP BY status_normalized, raw_status")).fetchall()
        for row in res:
            print(f"Norm: {row[0]:15} | Raw: {row[1]:20} | Count: {row[2]}")

if __name__ == "__main__":
    inspect_shopee()
    db.close()
