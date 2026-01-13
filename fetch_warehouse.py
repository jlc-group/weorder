
from app.core import get_db
from app.models.master import Warehouse
from sqlalchemy.orm import Session

try:
    db = next(get_db())
    warehouse = db.query(Warehouse).first()
    if warehouse:
        print(f"WAREHOUSE_ID: {warehouse.id}")
        print(f"WAREHOUSE_NAME: {warehouse.name}")
    else:
        print("No warehouse found.")
except Exception as e:
    print(f"Error: {e}")
