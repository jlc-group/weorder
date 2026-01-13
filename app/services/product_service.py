"""
Product Service - Business Logic for Products
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Tuple
from uuid import UUID

from app.models import Product, ProductSetBom
from app.schemas.product import ProductCreate, ProductUpdate

class ProductService:
    """Product business logic"""
    
    @staticmethod
    def get_products(
        db: Session,
        product_type: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[Product], int]:
        """Get products with filters and pagination"""
        query = db.query(Product)
        
        if active_only:
            query = query.filter(Product.is_active == True)
        
        if product_type:
            query = query.filter(Product.product_type == product_type)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Product.sku.ilike(search_term),
                    Product.name.ilike(search_term)
                )
            )
        
        total = query.count()
        
        products = query.order_by(Product.sku)\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
        
        return products, total
    
    @staticmethod
    def get_product_by_id(db: Session, product_id: UUID) -> Optional[Product]:
        """Get product by ID"""
        return db.query(Product).filter(Product.id == product_id).first()
    
    @staticmethod
    def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return db.query(Product).filter(Product.sku == sku).first()
    
    @staticmethod
    def create_product(db: Session, product_data: ProductCreate) -> Product:
        """Create new product"""
        product = Product(
            sku=product_data.sku,
            name=product_data.name,
            description=product_data.description,
            product_type=product_data.product_type,
            standard_cost=product_data.standard_cost,
            standard_price=product_data.standard_price,
            image_url=product_data.image_url
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def update_product(db: Session, product_id: UUID, product_data: ProductUpdate) -> Optional[Product]:
        """Update product"""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        
        for field, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def get_set_components(db: Session, set_product_id: UUID) -> List[dict]:
        """Get BOM components for a SET product"""
        bom_items = db.query(ProductSetBom).filter(
            ProductSetBom.set_product_id == set_product_id
        ).all()
        
        components = []
        for item in bom_items:
            component = db.query(Product).filter(Product.id == item.component_product_id).first()
            if component:
                components.append({
                    "product": component,
                    "quantity": item.quantity
                })
        
        return components

    @staticmethod
    def update_set_components(db: Session, product_id: UUID, components: List[dict]) -> bool:
        """
        Update components for a SET product
        components: list of dict {'product_id': UUID, 'quantity': int}
        """
        # 1. Verify product exists and is SET
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
            
        # Ensure it is a SET
        if product.product_type != "SET":
            product.product_type = "SET"
            db.add(product)
            
        # 2. Clear existing BOM
        db.query(ProductSetBom).filter(ProductSetBom.set_product_id == product_id).delete()
        
        # 3. Add new BOM
        for comp in components:
            comp_id = comp.get('product_id')
            qty = comp.get('quantity', 1)
            
            if not comp_id:
                continue
                
            # Check component existence? (Assume valid ID)
            bom = ProductSetBom(
                set_product_id=product_id,
                component_product_id=comp_id,
                quantity=qty
            )
            db.add(bom)
            
        db.commit()
        return True
