"""List all tables in weorder_db"""
import psycopg2
conn = psycopg2.connect(
    host="192.168.0.41",
    database="weorder_db",
    user="weorder_user",
    password="sZ3vlr2tzjz5x#T8",
    port=5432
)
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
for row in cur.fetchall():
    print(row[0])
cur.close()
conn.close()
