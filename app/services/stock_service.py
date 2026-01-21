"""
Stock Service - Business Logic for Inventory
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

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
                case(
                    (StockLedger.movement_type.in_(["IN", "RELEASE"]), StockLedger.quantity),
                    (StockLedger.movement_type.in_(["OUT", "RESERVE"]), -StockLedger.quantity),
                    (StockLedger.movement_type == "ADJUST", StockLedger.quantity),
                    else_=0
                )
            ).label("on_hand"),
            func.sum(
                case(
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
    def add_stock_movement(db: Session, movement_data: StockMovementCreate, created_by: Optional[UUID] = None, created_at_override: Optional[datetime] = None) -> StockLedger:
        """Add stock movement
        
        Args:
            created_at_override: If provided, use this as created_at instead of database default (now()).
                                 Useful for syncing historical data with correct dates.
        """
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
        
        # Override created_at if provided (for historical sync accuracy)
        if created_at_override:
            movement.created_at = created_at_override
        
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
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StockLedger]:
        """Get recent stock movements with optional date filter"""
        query = db.query(StockLedger)
        
        if warehouse_id:
            query = query.filter(StockLedger.warehouse_id == warehouse_id)
        
        if movement_type:
            query = query.filter(StockLedger.movement_type == movement_type)
        
        if start_date:
            query = query.filter(StockLedger.created_at >= start_date)
        
        if end_date:
            query = query.filter(StockLedger.created_at <= end_date)
        
        return query.order_by(StockLedger.created_at.desc()).limit(limit).all()

    @staticmethod
    def _resolve_components(db: Session, product_id: UUID, quantity: int) -> List[Dict]:
        """
        Recursively resolve product components from ProductSetBom.
        Returns list of {"product_id": uuid, "quantity": int} for atomic items.
        """
        from app.models.product import ProductSetBom
        
        # Check if this product is a set
        bom_items = db.query(ProductSetBom).filter(
            ProductSetBom.set_product_id == product_id
        ).all()
        
        if not bom_items:
            # Atomic (Base Case)
            return [{"product_id": product_id, "quantity": quantity}]
            
        # Recursive Step
        resolved = []
        for item in bom_items:
            # Multiply parent qty * component qty
            sub_qty = quantity * item.quantity
            resolved.extend(StockService._resolve_components(db, item.component_product_id, sub_qty))
            
        return resolved

    @staticmethod
    def process_order_deduction(db: Session, order, warehouse_id: UUID = None) -> bool:
        """
        Process stock deduction for an order based on Platform Listings (Bundles).
        Triggered when order becomes READY_TO_SHIP.
        """
        from app.models.mapping import PlatformListing, PlatformListingItem
        from app.models.product import Product
        
        # If warehouse_id not provided, pick default (First Active Warehouse)
        if not warehouse_id:
            wh = db.query(Warehouse).filter(Warehouse.is_active == True).first()
            if not wh:
                return False
            warehouse_id = wh.id

        # Check if already deducted to prevent double deduction
        existing_move = db.query(StockLedger).filter(
            StockLedger.reference_id == str(order.id),
            StockLedger.movement_type == 'OUT'
        ).first()
        
        if existing_move:
            # Already processed
            return True

        # Resolve Items
        items_to_deduct = [] # List of {product_id, quantity}

        # Iterate over order items (Platform SKUs)
        for order_item in order.items:
            # 1. Look up Platform Listing (Bundle Map)
            listing = db.query(PlatformListing).filter(
                PlatformListing.platform == order.channel_code,
                PlatformListing.platform_sku == order_item.sku
            ).first()

            if listing:
                # Found Bundle/Listing Map -> Use defined components
                for component in listing.items:
                    # Recursive Resolution
                    resolved = StockService._resolve_components(
                        db, 
                        component.product_id, 
                        component.quantity * order_item.quantity
                    )
                    items_to_deduct.extend(resolved)
            else:
                # Not Found -> Fallback: Try to find Master Product with same SKU
                master = db.query(Product).filter(Product.sku == order_item.sku).first()
                if master:
                    # Recursive Resolution
                    resolved = StockService._resolve_components(
                        db, 
                        master.id, 
                        order_item.quantity
                    )
                    items_to_deduct.extend(resolved)
                # If neither found, we can't deduct (maybe log warning)

        if not items_to_deduct:
            return False

        # Execute Deduction
        # Consolidate items first (e.g. 2 bundles might both contain Item A)
        consolidated = {}
        for item in items_to_deduct:
            pid = item["product_id"]
            if pid in consolidated:
                consolidated[pid] += item["quantity"]
            else:
                consolidated[pid] = item["quantity"]

        for pid, qty in consolidated.items():
            # Create OUT movement
            movement = StockLedger(
                warehouse_id=warehouse_id,
                product_id=pid,
                movement_type="OUT",
                quantity=qty,
                reference_type="ORDER",
                reference_id=str(order.id),
                note=f"Order {order.external_order_id} (RTS)"
            )
            db.add(movement)

        db.commit()
        return True

    @staticmethod
    def process_return(db: Session, order_id: UUID, items: List[dict], note: Optional[str] = None) -> bool:
        """
        Process a return for an order.
        items: List of dicts with keys: sku, quantity, condition, reason
        """
        from app.models.order import OrderHeader
        from app.models.product import Product

        # 1. Get Order
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            raise ValueError("Order not found")
        
        # 2. Prevent Double Return (Simple check)
        # If status is already RETURNED, we might still allow partial returns, 
        # but for now let's block if fully returned to be safe, 
        # OR we just rely on logic. 
        # Better: Log the return. If user returns same item twice, it's user error unless we track per-item return qty.
        # For this MVP, we trust the user input but ensure order exists.

        warehouse_id = order.warehouse_id
        if not warehouse_id:
             # Fallback to default
            wh = db.query(Warehouse).filter(Warehouse.is_active == True).first()
            if wh:
                warehouse_id = wh.id
            else:
                raise ValueError("No active warehouse to return to")

        # 3. Process Items
        for item in items:
            sku = item["sku"]
            qty = item["quantity"]
            condition = item["condition"] # GOOD or DAMAGED
            
            # Find Product ID from SKU
            product = db.query(Product).filter(Product.sku == sku).first()
            if not product:
                # If product not found (e.g. platform SKU vs internal SKU mismatch), 
                # we might need to resolve bundle? 
                # For now, assume direct SKU match or user selects internal SKU.
                # If user selects platform SKU, we need resolution.
                # Let's assume the frontend sends the "Product SKU" (internal).
                continue

            if condition == "GOOD":
                # Restock -> IN
                movement = StockLedger(
                    warehouse_id=warehouse_id,
                    product_id=product.id,
                    movement_type="IN", # Adds to Stock
                    quantity=qty,
                    reference_type="RETURN",
                    reference_id=str(order.id),
                    note=f"Return: {note or 'Restock'} ({item.get('reason','')})"
                )
                db.add(movement)
            else:
                # Damaged -> Log but do not add to sellable stock
                # We use specific type RETURN_DAMAGED which is NOT included in get_stock_summary on_hand
                movement = StockLedger(
                    warehouse_id=warehouse_id,
                    product_id=product.id,
                    movement_type="RETURN_DAMAGED",
                    quantity=qty,
                    reference_type="RETURN",
                    reference_id=str(order.id),
                    note=f"Return (Damaged): {note or ''} ({item.get('reason','')})"
                )
                db.add(movement)

        # 4. Update Order Status
        # If this is a partial return, we might want PARTIALLY_RETURNED
        # For simplicity, if any return happens, mark as RETURNED (or keep as is? User might want to flag it).
        # Let's set to RETURNED.
        order.status_normalized = "RETURNED"
        
        db.commit()
        return True
