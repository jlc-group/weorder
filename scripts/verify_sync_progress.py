
import sys
import os
from sqlalchemy import text
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from app.core import get_db
import logging

# Suppress SQL logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def check_sync_status():
    db = next(get_db())
    platforms = ['shopee', 'tiktok', 'lazada']
    output_lines = []
    try:
        output_lines.append("\n=== 2025 Order Sync Status ===")
        
        for platform in platforms:
            sql = text("""
                SELECT 
                    EXTRACT(MONTH FROM order_datetime) as month, 
                    COUNT(*) as count 
                FROM order_header 
                WHERE EXTRACT(YEAR FROM order_datetime) = 2025 
                AND channel_code = :platform
                GROUP BY month 
                ORDER BY month
            """)
            result = db.execute(sql, {"platform": platform}).fetchall()
            
            output_lines.append(f"\n[{platform.upper()}]")
            if not result:
                output_lines.append("  No orders found for 2025")
                continue
                
            total_orders = 0
            for row in result:
                month = int(row[0])
                count = row[1]
                total_orders += count
                output_lines.append(f"  Month {month:02d}: {count:,} orders")
            output_lines.append(f"  TOTAL: {total_orders:,}")

        output_lines.append("\n=== Log File Sizes ===")
        logs = [
            "sync_historical.log",
            "shopee_full_sync.log", 
            "tiktok_full_sync.log",
            "sync_finance_jan26.log"
        ]
        for log_name in logs:
            p = Path(log_name)
            if p.exists():
                size_mb = p.stat().st_size / (1024 * 1024)
                output_lines.append(f"{log_name}: {size_mb:.2f} MB")
            else:
                pass 

        with open("sync_status_report.txt", "w") as f:
            f.write("\n".join(output_lines))
        print("Report written to sync_status_report.txt")

    finally:
        db.close()

if __name__ == "__main__":
    check_sync_status()
