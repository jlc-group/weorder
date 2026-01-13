from sqlalchemy import create_engine, text

# Use chanack user
DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"
engine = create_engine(DATABASE_URL)

def check_empty_orders():
    with engine.connect() as conn:
        # Find order_headers on Jan 2nd (shipped_at/updated_at) that have NO order_items
        # and status is SHIPPED/DELIVERED/RETURNED
        
        sql = text("""
            SELECT h.id, h.external_order_id, h.channel_code, h.status_normalized, h.updated_at, h.shipped_at
            FROM order_header h
            LEFT JOIN order_item i ON h.id = i.order_id
            WHERE 
                h.status_normalized IN ('SHIPPED', 'DELIVERED', 'RETURNED')
                AND COALESCE(h.shipped_at, h.updated_at) >= '2026-01-02 00:00:00'
                AND COALESCE(h.shipped_at, h.updated_at) < '2026-01-03 00:00:00'
                AND i.id IS NULL
            LIMIT 10
        """)
        
        rows = conn.execute(sql).fetchall()
        print(f"Found {len(rows)} sample orders with NO items:")
        for r in rows:
            print(f" - [{r.channel_code}] ID: {r.external_order_id}, Status: {r.status_normalized}, Updated: {r.updated_at}, Shipped: {r.shipped_at}")

if __name__ == "__main__":
    check_empty_orders()
