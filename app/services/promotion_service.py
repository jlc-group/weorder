"""
Promotion Service - Business Logic for Promotions
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from app.models import Promotion, PromotionAction, OrderHeader, OrderItem, Product

class PromotionService:
    """Promotion business logic"""
    
    @staticmethod
    def get_promotions(
        db: Session,
        active_only: bool = True,
        channel: Optional[str] = None
    ) -> List[Promotion]:
        """Get promotions list"""
        query = db.query(Promotion)
        
        if active_only:
            query = query.filter(Promotion.is_active == True)
            now = datetime.now()
            query = query.filter(
                (Promotion.start_at == None) | (Promotion.start_at <= now)
            ).filter(
                (Promotion.end_at == None) | (Promotion.end_at >= now)
            )
        
        if channel:
            query = query.filter(
                (Promotion.channel_filter == None) |
                (Promotion.channel_filter == "all") |
                (Promotion.channel_filter == channel)
            )
        
        return query.order_by(Promotion.priority.desc()).all()
    
    @staticmethod
    def get_promotion_by_id(db: Session, promotion_id: UUID) -> Optional[Promotion]:
        """Get promotion by ID"""
        return db.query(Promotion).filter(Promotion.id == promotion_id).first()
    
    @staticmethod
    def create_promotion(
        db: Session,
        name: str,
        condition_type: str,
        condition_json: dict,
        actions: List[dict],
        **kwargs
    ) -> Promotion:
        """Create new promotion"""
        promotion = Promotion(
            name=name,
            condition_type=condition_type,
            condition_json=condition_json,
            **kwargs
        )
        
        for action_data in actions:
            action = PromotionAction(
                action_type=action_data.get("action_type", "ADD_FREE_ITEM"),
                free_product_id=action_data.get("free_product_id"),
                free_sku=action_data.get("free_sku"),
                free_quantity=action_data.get("free_quantity", 1)
            )
            promotion.actions.append(action)
        
        db.add(promotion)
        db.commit()
        db.refresh(promotion)
        return promotion
    
    @staticmethod
    def apply_promotions_to_order(db: Session, order: OrderHeader) -> List[OrderItem]:
        """Apply eligible promotions to an order"""
        applied_items = []
        
        # Get active promotions for this channel
        promotions = PromotionService.get_promotions(
            db, 
            active_only=True, 
            channel=order.channel_code
        )
        
        for promo in promotions:
            if PromotionService._check_condition(order, promo):
                # Apply promotion actions
                for action in promo.actions:
                    if action.action_type == "ADD_FREE_ITEM" and action.free_product_id:
                        product = db.query(Product).filter(
                            Product.id == action.free_product_id
                        ).first()
                        
                        if product:
                            free_item = OrderItem(
                                order_id=order.id,
                                product_id=product.id,
                                sku=product.sku,
                                product_name=product.name,
                                quantity=action.free_quantity or 1,
                                unit_price=Decimal("0"),
                                line_discount=Decimal("0"),
                                line_total=Decimal("0"),
                                line_type="FREE_PROMO",
                                promotion_id=promo.id
                            )
                            db.add(free_item)
                            applied_items.append(free_item)
                
                # Update order discount label
                if not order.order_discount_label:
                    order.order_discount_label = promo.name
                else:
                    order.order_discount_label += f", {promo.name}"
        
        if applied_items:
            db.commit()
        
        return applied_items
    
    @staticmethod
    def _check_condition(order: OrderHeader, promotion: Promotion) -> bool:
        """Check if order meets promotion condition"""
        if promotion.condition_type == "MIN_ORDER_AMOUNT":
            min_amount = promotion.condition_json.get("min_amount", 0)
            return float(order.subtotal_amount or 0) >= float(min_amount)
        
        elif promotion.condition_type == "MIN_QTY":
            min_qty = promotion.condition_json.get("min_qty", 0)
            total_qty = sum(item.quantity for item in order.items if item.line_type == "NORMAL")
            return total_qty >= min_qty
        
        elif promotion.condition_type == "SKU_CONTAINS":
            required_skus = promotion.condition_json.get("skus", [])
            order_skus = [item.sku for item in order.items]
            return any(sku in order_skus for sku in required_skus)
        
        return False
    
    @staticmethod
    def toggle_promotion(db: Session, promotion_id: UUID) -> Optional[Promotion]:
        """Toggle promotion active status"""
        promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
        if promotion:
            promotion.is_active = not promotion.is_active
            db.commit()
            db.refresh(promotion)
        return promotion
