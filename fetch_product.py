
from app.core import get_db
from app.models.product import Product
from sqlalchemy.orm import Session
import uuid

try:
    db = next(get_db())
    product = db.query(Product).first()
    if product:
        print(f"PRODUCT_ID: {product.id}")
        print(f"PRODUCT_SKU: {product.sku}")
    else:
        # Create one if missing
        new_prod = Product(
            id=uuid.uuid4(),
            sku="TEST-SKU-REAL",
            name="Real Test Product",
            company_id=uuid.UUID("54c3b509-1de7-4f87-9846-b9f65d40f3b3") # Use existing company from prev logs if possible, or just fetch company
        )
        db.add(new_prod)
        db.commit()
        print(f"CREATED_PRODUCT_ID: {new_prod.id}")
except Exception as e:
    print(f"Error: {e}")
