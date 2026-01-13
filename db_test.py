
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from app.core.database import SessionLocal
from app.models.master import Company
print("Connecting to DB...")
db = SessionLocal()
try:
    company = db.query(Company).first()
    print(f"Success! Company: {company.name if company else 'None'}")
finally:
    db.close()
