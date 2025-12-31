"""
Stock Service - Business Logic for Inventory
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from uuid import UUID

from app.models import StockLedger, Product, Warehouse
from app.schemas.stock import StockMovementCreate

class StockService:
    """Stock/Inventory business logic"""
    
    @staticmethod
    def get_stock_summary(
        db: Session,
        warehouse_id: Optional[UUID] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """Get stock summary by product and warehouse"""
        # Subquery for movements
        movements_query = db.query(
            StockLedger.warehouse_id,
            StockLedger.product_id,
            func.sum(
                func.case(
                    (StockLedger.movement_type.in_(["IN", "RELEASE"]), StockLedger.quantity),
                    (StockLedger.movement_type.in_(["OUT", "RESERVE"]), -StockLedger.quantity),
                    (StockLedger.movement_type == "ADJUST", StockLedger.quantity),
                    else_=0
                )
            ).label("on_hand"),
            func.sum(
                func.case(
                    (StockLedger.movement_type == "RESERVE", StockLedger.quantity),
                    (StockLedger.movement_type == "RELEASE", -StockLedger.quantity),
                    else_=0
                )
            ).label("reserved")
        ).group_by(
            StockLedger.warehouse_id,
            StockLedger.product_id
        )
        
        if warehouse_id:
            movements_query = movements_query.filter(StockLedger.warehouse_id == warehouse_id)
        
        movements = movements_query.all()
        
        results = []
        for m in movements:
            product = db.query(Product).filter(Product.id == m.product_id).first()
            warehouse = db.query(Warehouse).filter(Warehouse.id == m.warehouse_id).first()
            
            if product and warehouse:
                if search:
                    search_term = search.lower()
                    if search_term not in product.sku.lower() and search_term not in product.name.lower():
                        continue
                
                on_hand = int(m.on_hand or 0)
                reserved = int(m.reserved or 0)
                
                results.append({
                    "product_id": product.id,
                    "sku": product.sku,
                    "product_name": product.name,
                    "warehouse_id": warehouse.id,
                    "warehouse_name": warehouse.name,
                    "on_hand": on_hand,
                    "reserved": reserved,
                    "available": on_hand - reserved
                })
        
        return results
    
    @staticmethod
    def add_stock_movement(db: Session, movement_data: StockMovementCreate, created_by: Optional[UUID] = None) -> StockLedger:
        """Add stock movement"""
        movement = StockLedger(
            warehouse_id=movement_data.warehouse_id,
            product_id=movement_data.product_id,
            movement_type=movement_data.movement_type,
            quantity=movement_data.quantity,
            reference_type=movement_data.reference_type,
            reference_id=movement_data.reference_id,
            note=movement_data.note,
            created_by=created_by
        )
        
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement
    
    @staticmethod
    def reserve_stock_for_order(db: Session, order_id: UUID, warehouse_id: UUID, items: List[dict]) -> bool:
        """Reserve stock for an order"""
        for item in items:
            movement = StockLedger(
                warehouse_id=warehouse_id,
                product_id=item["product_id"],
                movement_type="RESERVE",
                quantity=item["quantity"],
                reference_type="ORDER",
                reference_id=str(order_id)
            )
            db.add(movement)
        
        db.commit()
        return True
    
    @staticmethod
    def consume_stock_for_order(db: Session, order_id: UUID, warehouse_id: UUID, items: List[dict]) -> bool:
        """Consume reserved stock when order ships"""
        for item in items:
            # Release reservation
            release = StockLedger(
                warehouse_id=warehouse_id,
                product_id=item["product_id"],
                movement_type="RELEASE",
                quantity=item["quantity"],
                reference_type="ORDER",
                reference_id=str(order_id)
            )
            db.add(release)
            
            # Consume stock
            consume = StockLedger(
                warehouse_id=warehouse_id,
                product_id=item["product_id"],
                movement_type="OUT",
                quantity=item["quantity"],
                reference_type="ORDER",
                reference_id=str(order_id)
            )
            db.add(consume)
        
        db.commit()
        return True
    
    @staticmethod
    def get_recent_movements(
        db: Session,
        warehouse_id: Optional[UUID] = None,
        movement_type: Optional[str] = None,
        limit: int = 50
    ) -> List[StockLedger]:
        """Get recent stock movements"""
        query = db.query(StockLedger)
        
        if warehouse_id:
            query = query.filter(StockLedger.warehouse_id == warehouse_id)
        
        if movement_type:
            query = query.filter(StockLedger.movement_type == movement_type)
        
        return query.order_by(StockLedger.created_at.desc()).limit(limit).all()
