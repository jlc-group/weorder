
from app.core import get_db
from app.models.master import Warehouse, Company
from sqlalchemy.orm import Session
import uuid

try:
    db = next(get_db())
    # Ensure company exists
    company = db.query(Company).first()
    if not company:
        company = Company(id=uuid.uuid4(), name="Test Company", code="TC01")
        db.add(company)
        db.commit()
    
    warehouse = Warehouse(
        id=uuid.uuid4(),
        company_id=company.id,
        name="Main Warehouse",
        code="WH01",
        is_active=True
    )
    db.add(warehouse)
    db.commit()
    print(f"CREATED_WAREHOUSE_ID: {warehouse.id}")
except Exception as e:
    print(f"Error: {e}")
