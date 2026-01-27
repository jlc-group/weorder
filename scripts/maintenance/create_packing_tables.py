"""
Create PackingBatch tables
"""
import psycopg2
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host="192.168.0.41",
    database="weorder_db",
    user="weorder_user",
    password="sZ3vlr2tzjz5x#T8",
    port=5432
)
cur = conn.cursor()

print("Creating packing_batch table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS packing_batch (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        batch_number INTEGER NOT NULL,
        batch_date TIMESTAMP WITH TIME ZONE NOT NULL,
        synced_at TIMESTAMP WITH TIME ZONE,
        cutoff_at TIMESTAMP WITH TIME ZONE,
        order_count INTEGER DEFAULT 0,
        packed_count INTEGER DEFAULT 0,
        printed_count INTEGER DEFAULT 0,
        status VARCHAR(20) DEFAULT 'PENDING',
        platform VARCHAR(30),
        notes TEXT,
        created_by VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
""")

print("Creating packing_batch_order table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS packing_batch_order (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        batch_id UUID NOT NULL REFERENCES packing_batch(id) ON DELETE CASCADE,
        order_id UUID NOT NULL REFERENCES order_header(id),
        is_packed BOOLEAN DEFAULT FALSE,
        is_printed BOOLEAN DEFAULT FALSE,
        packed_at TIMESTAMP WITH TIME ZONE,
        printed_at TIMESTAMP WITH TIME ZONE,
        sequence INTEGER
    )
""")

print("Creating indexes...")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_packing_batch_date ON packing_batch(batch_date);
    CREATE INDEX IF NOT EXISTS idx_packing_batch_status ON packing_batch(status);
    CREATE INDEX IF NOT EXISTS idx_packing_batch_order_batch ON packing_batch_order(batch_id);
    CREATE INDEX IF NOT EXISTS idx_packing_batch_order_order ON packing_batch_order(order_id);
""")

conn.commit()
print("Done!")

cur.close()
conn.close()
