from sqlalchemy import create_engine, text
import os

# Manual config to avoid imports
# Trying 'chanack' as user, assuming local Postgres app behavior
DATABASE_URL = "postgresql://chanack@localhost:5432/weorder"

engine = create_engine(DATABASE_URL)

target_id = "581693998548878727"

with engine.connect() as conn:
    print("Checking order:", target_id)
    result = conn.execute(text(f"SELECT shipped_at, updated_at, status_normalized FROM order_header WHERE external_order_id = '{target_id}'"))
    row = result.fetchone()
    
    if row:
        print(f"Shipped At: {row[0]}")
        print(f"Updated At: {row[1]}")
        print(f"Status: {row[2]}")
    else:
        print("Order not found")
        
    print("-" * 20)
    # Check count of orders shipped_at != updated_at (approx)
    # This indicates backfill is working (diverging values)
    
    diff_count = conn.execute(text("SELECT count(*) FROM order_header WHERE shipped_at IS NOT NULL AND status_normalized = 'SHIPPED' AND shipped_at != updated_at")).scalar()
    print(f"Orders with distinct shipped_at (indicating fix): {diff_count}")
