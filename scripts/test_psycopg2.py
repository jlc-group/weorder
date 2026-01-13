
print("Start psycopg2 test")
import psycopg2
print("Imported psycopg2")
try:
    conn = psycopg2.connect("dbname=weorder user=chanack host=localhost")
    print("Connected to DB")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print(cur.fetchone())
    conn.close()
    print("Closed DB")
except Exception as e:
    print(f"Error: {e}")
