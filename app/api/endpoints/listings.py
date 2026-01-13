from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.models import PlatformListing, PlatformListingItem, Product

router = APIRouter()

# --- Pydantic Schemas ---

class ListingItemCreate_DTO(BaseModel):
    product_id: UUID
    quantity: int = 1

class ListingCreate_DTO(BaseModel):
    platform: str
    platform_sku: str
    name: Optional[str] = None
    items: List[ListingItemCreate_DTO]

class ListingItem_DTO(BaseModel):
    id: UUID
    product_id: UUID
    product_sku: str # Show master SKU for convenience
    quantity: int
    
    class Config:
        from_attributes = True

class Listing_DTO(BaseModel):
    id: UUID
    platform: str
    platform_sku: str
    name: Optional[str] = None
    items: List[ListingItem_DTO]
    
    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/", response_model=List[Listing_DTO])
def get_listings(
    platform: Optional[str] = None, 
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List platform listings with optional filters"""
    query = db.query(PlatformListing)
    
    if platform:
        query = query.filter(PlatformListing.platform == platform)
        
    if search:
        query = query.filter(
            (PlatformListing.platform_sku.ilike(f"%{search}%")) |
            (PlatformListing.name.ilike(f"%{search}%"))
        )
        
    listings = query.all()
    
    # Process result to include product_sku in items manually if needed, 
    # but Pydantic + ORM can handle it if we add a property or join.
    # For simplicity, let's map it.
    
    results = []
    for listing in listings:
        items_dto = []
        for item in listing.items:
            # Safe guard if product is missing (deleted?)
            p_sku = item.product.sku if item.product else "UNKNOWN"
            items_dto.append(ListingItem_DTO(
                id=item.id,
                product_id=item.product_id,
                product_sku=p_sku,
                quantity=item.quantity
            ))
        
        results.append(Listing_DTO(
            id=listing.id,
            platform=listing.platform,
            platform_sku=listing.platform_sku,
            name=listing.name,
            items=items_dto
        ))
        
    return results

@router.post("/", response_model=Listing_DTO)
def create_listing(payload: ListingCreate_DTO, db: Session = Depends(get_db)):
    """Create a new platform listing mapping"""
    # Check duplicate
    existing = db.query(PlatformListing).filter(
        PlatformListing.platform == payload.platform,
        PlatformListing.platform_sku == payload.platform_sku
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Listing for {payload.platform} SKU {payload.platform_sku} already exists")
    
    # Create Listing
    new_listing = PlatformListing(
        platform=payload.platform,
        platform_sku=payload.platform_sku,
        name=payload.name or payload.platform_sku
    )
    db.add(new_listing)
    db.flush() # Get ID
    
    # Create Items
    for item_data in payload.items:
        # Verify product exists
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            continue # Or raise error
            
        new_item = PlatformListingItem(
            listing_id=new_listing.id,
            product_id=product.id,
            quantity=item_data.quantity
        )
        db.add(new_item)
        
    db.commit()
    db.refresh(new_listing)
    
    # Return DTO
    items_dto = []
    for item in new_listing.items:
        p_sku = item.product.sku if item.product else "UNKNOWN"
        items_dto.append(ListingItem_DTO(
            id=item.id,
            product_id=item.product_id,
            product_sku=p_sku,
            quantity=item.quantity
        ))
        
    return Listing_DTO(
        id=new_listing.id,
        platform=new_listing.platform,
        platform_sku=new_listing.platform_sku,
        name=new_listing.name,
        items=items_dto
    )
@router.put("/{id}", response_model=Listing_DTO)
def update_listing(id: UUID, payload: ListingCreate_DTO, db: Session = Depends(get_db)):
    """
    Update an existing listing.
    - Updates simple fields (name).
    - FULL REPLACE of items: Deletes old items, creates new ones.
    """
    # 1. Find Listing
    listing = db.query(PlatformListing).filter(PlatformListing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    # 2. Update simple fields
    if payload.name:
        listing.name = payload.name
        
    # Note: We usually don't allow changing platform/sku as it's the key, 
    # but if needed we could. For now, let's assume those remain fixed or are ignored.
    
    # 3. Full Replace Items
    # a. Delete existing items
    db.query(PlatformListingItem).filter(PlatformListingItem.listing_id == id).delete()
    
    # b. Create new items
    for item_data in payload.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not product:
            continue
            
        new_item = PlatformListingItem(
            listing_id=listing.id,
            product_id=product.id,
            quantity=item_data.quantity
        )
        db.add(new_item)
        
    db.commit()
    db.refresh(listing)
    
    # Return DTO
    items_dto = []
    for item in listing.items:
        p_sku = item.product.sku if item.product else "UNKNOWN"
        items_dto.append(ListingItem_DTO(
            id=item.id,
            product_id=item.product_id,
            product_sku=p_sku,
            quantity=item.quantity
        ))
        
    return Listing_DTO(
        id=listing.id,
        platform=listing.platform,
        platform_sku=listing.platform_sku,
        name=listing.name,
        items=items_dto
    )
@router.delete("/{id}")
def delete_listing(id: UUID, db: Session = Depends(get_db)):
    """Delete a listing"""
    listing = db.query(PlatformListing).filter(PlatformListing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    db.delete(listing)
    db.commit()
    return {"message": "Deleted successfully"}

@router.post("/import-from-history")
def import_from_history(db: Session = Depends(get_db)):
    """
    Auto-import listings from order history.
    Finds distinct Platform SKU + Platform combinations.
    If not exists, creates a new PlatformListing.
    Tries to map to Master Product if SKU matches exactly.
    """
    from sqlalchemy import text
    
    # 1. Query distinct aggregate data
    sql = """
    SELECT 
        oh.channel_code,
        oi.sku,
        MAX(oi.product_name) as sample_name
    FROM order_header oh
    JOIN order_item oi ON oh.id = oi.order_id
    GROUP BY oh.channel_code, oi.sku
    """
    
    results = db.execute(text(sql)).fetchall()
    
    imported_count = 0
    skipped_count = 0
    
    for row in results:
        channel = row[0]
        p_sku = row[1]
        p_name = row[2]
        
        # Check if exists
        exists = db.query(PlatformListing).filter(
            PlatformListing.platform == channel,
            PlatformListing.platform_sku == p_sku
        ).first()
        
        if exists:
            skipped_count += 1
            continue
            
        # Create Listing
        new_listing = PlatformListing(
            platform=channel,
            platform_sku=p_sku,
            name=p_name or p_sku
        )
        db.add(new_listing)
        db.flush() 
        
        # Try to auto-map to Master Product (Exact Match)
        master_product = db.query(Product).filter(Product.sku == p_sku).first()
        if master_product:
             item_map = PlatformListingItem(
                 listing_id=new_listing.id,
                 product_id=master_product.id,
                 quantity=1 # Default assumption
             )
             db.add(item_map)
        
        imported_count += 1
        
    db.commit()
    
    return {
        "success": True, 
        "imported": imported_count, 
        "skipped": skipped_count,
        "message": f"Imported {imported_count} listings from history"
    }
