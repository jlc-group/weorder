from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

def check_channels():
    with engine.connect() as conn:
        print("--- Orders appearing on Jan 2nd Report (by Channel) ---")
        sql = text("""
            SELECT channel_code, COUNT(*) 
            FROM order_header 
            WHERE 
                status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED', 'TO_RETURN', 'RETURN_INITIATED')
                AND COALESCE(shipped_at, updated_at) >= '2026-01-02 00:00:00'
                AND COALESCE(shipped_at, updated_at) < '2026-01-03 00:00:00'
            GROUP BY channel_code
        """)
        rows = conn.execute(sql).fetchall()
        for r in rows:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    check_channels()
