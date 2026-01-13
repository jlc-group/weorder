
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
from sqlalchemy import text

def clean_data():
    db = next(get_db())
    try:
        print("\n=== Cleaning Invalid Invoice Profiles ===")
        
        # 1. Count before
        result = db.execute(text("""
            SELECT count(*) 
            FROM invoice_profile 
            WHERE platform_invoice_data->>'source_type' = 'SHIPPING_FALLBACK'
        """))
        count = result.scalar()
        print(f"Found {count} records to delete.")
        
        if count == 0:
            print("Nothing to clean.")
            return

        # 2. Delete
        print("Deleting...")
        db.execute(text("""
            DELETE FROM invoice_profile 
            WHERE platform_invoice_data->>'source_type' = 'SHIPPING_FALLBACK'
        """))
        db.commit()
        
        # 3. Verify
        result = db.execute(text("""
            SELECT count(*) 
            FROM invoice_profile 
            WHERE platform_invoice_data->>'source_type' = 'SHIPPING_FALLBACK'
        """))
        remaining = result.scalar()
        print(f"Deletion complete. Remaining: {remaining}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_data()
