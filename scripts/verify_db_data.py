
import asyncio
import logging
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
from sqlalchemy import text

def verify_data():
    db = next(get_db())
    try:
        print("\n=== Invoice Profile Verification ===")
        
        # 1. Count totals
        result = db.execute(text("SELECT count(*) FROM invoice_profile"))
        total_count = result.scalar()
        print(f"Total Invoice Profiles: {total_count}")
        
        # 2. Count by source_type (Shopee only)
        result = db.execute(text("""
            SELECT 
                platform_invoice_data->>'source_type' as source_type, 
                count(*) as count 
            FROM invoice_profile 
            WHERE CAST(platform_invoice_data AS TEXT) LIKE '%SHOPEE%'
            GROUP BY platform_invoice_data->>'source_type'
        """))
        print("\nBreakdown by Source Type:")
        rows = result.fetchall()
        for row in rows:
            print(f"  - {row[0] or 'Unknown'}: {row[1]}")
            
        # 3. Show a valid one if exists
        print("\n=== Sample Valid Official Request (if any) ===")
        result = db.execute(text("""
            SELECT 
                order_id, 
                invoice_name, 
                tax_id
            FROM invoice_profile 
            WHERE platform_invoice_data->>'source_type' = 'OFFICIAL_REQUEST'
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            print(f"Found valid: {row[1]} (Tax: {row[2]})")
        else:
            print("No OFFICIAL_REQUEST records found.")

        # 4. Check for potential issues (e.g. missing crucial data)
        print("\n=== Potential Issues ===")
        result = db.execute(text("""
            SELECT count(*) FROM invoice_profile 
            WHERE tax_id IS NULL OR tax_id = ''
        """))
        missing_tax = result.scalar()
        if missing_tax > 0:
            print(f"⚠️  Found {missing_tax} records with missing Tax ID")
        else:
            print("✅ All records have Tax ID")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
