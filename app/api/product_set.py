from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core import get_db
from app.models.product import Product, ProductSetBom
from app.schemas.product import ProductSetBOMUpdate, ProductSetComponent

router = APIRouter(prefix="/products", tags=["Product Sets"])

@router.get("/{product_id}/bom", response_model=List[ProductSetComponent])
def get_product_bom(product_id: UUID, db: Session = Depends(get_db)):
    """Get BOM components for a product set"""
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    bom_items = db.query(ProductSetBom).filter(ProductSetBom.set_product_id == product_id).all()
    
    result = []
    for bom in bom_items:
        comp = db.query(Product).get(bom.component_product_id)
        if comp:
            result.append({
                "product_id": bom.component_product_id,
                "quantity": bom.quantity,
                "sku": comp.sku,
                "name": comp.name
            })
    
    return result

@router.put("/{product_id}/bom")
def update_product_bom(product_id: UUID, data: ProductSetBOMUpdate, db: Session = Depends(get_db)):
    """Update BOM components for a product set"""
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        # 1. Update product type to SET
        product.product_type = "SET"
        
        # 2. Clear existing BOM
        db.query(ProductSetBom).filter(ProductSetBom.set_product_id == product_id).delete()
        
        # 3. Add new components
        for comp in data.components:
            # Verify component exists
            component = db.query(Product).get(comp.product_id)
            if not component:
                raise HTTPException(status_code=400, detail=f"Component product {comp.product_id} not found")
                
            new_bom = ProductSetBom(
                set_product_id=product_id,
                component_product_id=comp.product_id,
                quantity=comp.quantity
            )
            db.add(new_bom)
            
        db.commit()
        return {"success": True, "message": "Product set updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
