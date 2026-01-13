
import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

def check_volume():
    db = SessionLocal()
    try:
        # Check Jan 8, 2025
        query_2025 = text("""
            SELECT count(*) FROM order_header
            WHERE shipped_at >= '2025-01-08 00:00:00'
            AND shipped_at <= '2025-01-08 23:59:59'
        """)
        count_2025 = db.execute(query_2025).scalar()
        print(f"Orders on Jan 8, 2025: {count_2025}")

        # Check Jan 5, 2026
        query_2026 = text("""
            SELECT count(*) FROM order_header
            WHERE shipped_at >= '2026-01-05 00:00:00'
            AND shipped_at <= '2026-01-05 23:59:59'
        """)
        count_2026 = db.execute(query_2026).scalar()
        print(f"Orders on Jan 5, 2026: {count_2026}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_volume()
