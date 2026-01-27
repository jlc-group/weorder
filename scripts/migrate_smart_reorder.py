import os
import sys
from sqlalchemy import text

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import engine

def migrate():
    print("Migrating database...")
    with engine.connect() as conn:
        with conn.begin():
            # Add target_days_to_keep
            try:
                conn.execute(text("ALTER TABLE product ADD COLUMN target_days_to_keep INTEGER DEFAULT 30"))
                print("Added column: target_days_to_keep")
            except Exception as e:
                print(f"Skipped target_days_to_keep (might exist): {e}")
                
            # Add lead_time_days
            try:
                conn.execute(text("ALTER TABLE product ADD COLUMN lead_time_days INTEGER DEFAULT 7"))
                print("Added column: lead_time_days")
            except Exception as e:
                print(f"Skipped lead_time_days (might exist): {e}")

if __name__ == "__main__":
    migrate()
