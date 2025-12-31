"""
Order Service - Business Logic for Orders
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from app.models import OrderHeader, OrderItem, Product, AuditLog
from app.schemas.order import OrderCreate, OrderUpdate

class OrderService:
    """Order business logic"""
    
    # Valid status transitions
    STATUS_TRANSITIONS = {
        "NEW": ["PAID", "CANCELLED"],
        "PAID": ["PACKING", "CANCELLED"],
        "PACKING": ["SHIPPED", "PAID"],
        "SHIPPED": ["DELIVERED", "RETURNED"],
        "DELIVERED": ["RETURNED"],
        "RETURNED": [],
        "CANCELLED": [],
    }
    
    @staticmethod
    def get_orders(
        db: Session,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[OrderHeader], int]:
        """Get orders with filters and pagination"""
        query = db.query(OrderHeader)
        
        if channel and channel != "all":
            query = query.filter(OrderHeader.channel_code == channel)
        
        if status and status != "all":
            query = query.filter(OrderHeader.status_normalized == status)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    OrderHeader.external_order_id.ilike(search_term),
                    OrderHeader.customer_name.ilike(search_term),
                    OrderHeader.customer_phone.ilike(search_term)
                )
            )
        
        total = query.count()
        
        orders = query.order_by(OrderHeader.created_at.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
        
        return orders, total
    
    @staticmethod
    def get_order_by_id(db: Session, order_id: UUID) -> Optional[OrderHeader]:
        """Get order by ID"""
        return db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
    
    @staticmethod
    def get_order_by_external_id(db: Session, external_id: str) -> Optional[OrderHeader]:
        """Get order by external order ID"""
        return db.query(OrderHeader).filter(OrderHeader.external_order_id == external_id).first()
    
    @staticmethod
    def create_order(db: Session, order_data: OrderCreate, created_by: Optional[UUID] = None) -> OrderHeader:
        """Create new order"""
        # Generate external order ID if not provided
        if not order_data.external_order_id:
            today = datetime.now().strftime("%Y%m%d")
            count = db.query(OrderHeader).filter(
                OrderHeader.external_order_id.like(f"MAN-{today}%")
            ).count()
            order_data.external_order_id = f"MAN-{today}-{count + 1:04d}"
        
        # Create order header
        order = OrderHeader(
            external_order_id=order_data.external_order_id,
            channel_code=order_data.channel_code,
            company_id=order_data.company_id,
            warehouse_id=order_data.warehouse_id,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            customer_address=order_data.customer_address,
            payment_method=order_data.payment_method,
            shipping_method=order_data.shipping_method,
            shipping_fee=order_data.shipping_fee,
            discount_amount=order_data.discount_amount,
            status_normalized="NEW",
            order_datetime=datetime.now(),
            created_by=created_by
        )
        
        # Calculate totals
        subtotal = Decimal("0")
        for item_data in order_data.items:
            product = db.query(Product).filter(Product.id == item_data.product_id).first() if item_data.product_id else None
            
            item = OrderItem(
                product_id=item_data.product_id,
                sku=item_data.sku,
                product_name=item_data.product_name or (product.name if product else item_data.sku),
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                line_discount=item_data.line_discount,
                line_type=item_data.line_type
            )
            item.line_total = (item.unit_price * item.quantity) - item.line_discount
            subtotal += item.line_total
            order.items.append(item)
        
        order.subtotal_amount = subtotal
        order.total_amount = subtotal + order.shipping_fee - order.discount_amount
        
        db.add(order)
        db.commit()
        db.refresh(order)
        
        return order
    
    @staticmethod
    def update_order(db: Session, order_id: UUID, order_data: OrderUpdate) -> Optional[OrderHeader]:
        """Update order"""
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            return None
        
        for field, value in order_data.model_dump(exclude_unset=True).items():
            setattr(order, field, value)
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def update_status(db: Session, order_id: UUID, new_status: str, performed_by: Optional[UUID] = None) -> Tuple[bool, str]:
        """Update order status with validation"""
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            return False, "Order not found"
        
        current_status = order.status_normalized
        allowed = OrderService.STATUS_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed:
            return False, f"Cannot transition from {current_status} to {new_status}"
        
        old_status = order.status_normalized
        order.status_normalized = new_status
        
        # Create audit log
        audit = AuditLog(
            table_name="order_header",
            record_id=str(order_id),
            action="STATUS_CHANGE",
            performed_by=performed_by,
            before_data={"status_normalized": old_status},
            after_data={"status_normalized": new_status}
        )
        db.add(audit)
        
        db.commit()
        return True, "Status updated successfully"
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> dict:
        """Get dashboard statistics"""
        today = datetime.now().date()
        
        # Count by status
        status_counts = db.query(
            OrderHeader.status_normalized,
            func.count(OrderHeader.id)
        ).group_by(OrderHeader.status_normalized).all()
        
        # Today's orders
        today_count = db.query(func.count(OrderHeader.id)).filter(
            func.date(OrderHeader.created_at) == today
        ).scalar()
        
        # Today's revenue
        today_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            func.date(OrderHeader.created_at) == today,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        return {
            "status_counts": dict(status_counts),
            "today_orders": today_count,
            "today_revenue": float(today_revenue)
        }
