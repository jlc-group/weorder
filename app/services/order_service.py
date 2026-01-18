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
from app.schemas.stock import StockMovementCreate
from .stock_service import StockService

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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        exclude_cancelled: bool = False
    ) -> Tuple[List[OrderHeader], int]:
        """Get orders with filters and pagination"""
        query = db.query(OrderHeader)
         
        # Timezone handling for date filters
        if start_date or end_date:
            from app.core import settings
            from zoneinfo import ZoneInfo
            from datetime import datetime, timezone
            
            try:
                tz = ZoneInfo(settings.TIMEZONE)
            except:
                tz = ZoneInfo("UTC")

            if start_date:
                # Parse YYYY-MM-DD
                s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                # Start of day in local time -> UTC
                s_dt = datetime.combine(s_date, datetime.min.time()).replace(tzinfo=tz)
                s_dt_utc = s_dt.astimezone(timezone.utc)
                query = query.filter(OrderHeader.order_datetime >= s_dt_utc)
                
            if end_date:
                # Parse YYYY-MM-DD
                e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                # End of day in local time -> UTC
                e_dt = datetime.combine(e_date, datetime.max.time()).replace(tzinfo=tz)
                e_dt_utc = e_dt.astimezone(timezone.utc)
                query = query.filter(OrderHeader.order_datetime <= e_dt_utc)
        
        if channel and channel != "all":
            query = query.filter(OrderHeader.channel_code == channel)
        
        if status and status != "all":
            if "," in status:
                status_list = [s.strip() for s in status.split(",")]
                query = query.filter(OrderHeader.status_normalized.in_(status_list))
            else:
                query = query.filter(OrderHeader.status_normalized == status)
        
        # Exclude cancelled orders if requested
        if exclude_cancelled:
            query = query.filter(OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"]))
        
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
        
        orders = query.order_by(OrderHeader.order_datetime.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
        
        return orders, total
    
    @staticmethod
    def get_orders_by_sku_qty(
        db: Session,
        sku_qty_filters: List[str],  # Format: ["L14-70G:2", "L3-40G:1"]
        channel: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[OrderHeader], int]:
        """Get orders filtered by SKU + consolidated quantity"""
        # Build subquery to get order_ids matching the SKU+qty criteria
        from sqlalchemy import text, literal
        
        # Parse sku_qty filters
        sku_qty_conditions = []
        for filter_str in sku_qty_filters:
            parts = filter_str.split(":")
            if len(parts) == 2:
                sku, qty_str = parts
                qty = int(qty_str)
                sku_qty_conditions.append((sku, qty))
        
        if not sku_qty_conditions:
            return [], 0
        
        # Subquery: get order_ids where sum(quantity) for SKU matches target qty
        matching_order_ids = set()
        
        for sku, target_qty in sku_qty_conditions:
            # Get orders with this SKU having the target consolidated quantity
            subq = db.query(OrderItem.order_id)\
                .join(OrderHeader)\
                .filter(OrderItem.sku == sku)
            
            # Apply status filter
            if status and status != "all":
                if "," in status:
                    status_list = [s.strip() for s in status.split(",")]
                    subq = subq.filter(OrderHeader.status_normalized.in_(status_list))
                else:
                    subq = subq.filter(OrderHeader.status_normalized == status)
            
            if channel and channel != "all" and channel != "ALL":
                subq = subq.filter(func.lower(OrderHeader.channel_code) == channel.lower())
            
            # Group by order and filter by sum(qty)
            subq = subq.group_by(OrderItem.order_id)\
                .having(func.sum(OrderItem.quantity) == target_qty if target_qty < 3 else func.sum(OrderItem.quantity) >= 3)
            
            order_ids = [r[0] for r in subq.all()]
            matching_order_ids.update(order_ids)
        
        if not matching_order_ids:
            return [], 0
        
        # Now fetch the actual orders
        query = db.query(OrderHeader).filter(OrderHeader.id.in_(matching_order_ids))
        
        total = query.count()
        
        orders = query.order_by(OrderHeader.order_datetime.desc())\
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
    def update_status(db: Session, order_id: UUID, new_status: str, performed_by: Optional[UUID] = None, status_changed_at: Optional[datetime] = None) -> Tuple[bool, str]:
        """Update order status with validation
        
        Args:
            status_changed_at: If provided, use this as the date for stock movements.
                              Useful for syncing historical data with correct dates.
        """
        order = db.query(OrderHeader).filter(OrderHeader.id == order_id).first()
        if not order:
            return False, "Order not found"
        
        current_status = order.status_normalized
        allowed = OrderService.STATUS_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed:
            return False, f"Cannot transition from {current_status} to {new_status}"
        
        old_status = order.status_normalized
        order.status_normalized = new_status
        
        # Capture ship date
        if new_status in ["SHIPPED", "DELIVERED"] and not order.shipped_at:
             order.shipped_at = status_changed_at or datetime.now()
        
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

        # --- Stock Movement Logic ---
        try:
            # SHIPPED or COMPLETED (if skipped SHIPPED) -> Deduct Stock
            # We check if it's the FIRST time reaching this state? 
            # Or simplified: If new_status in [SHIPPED, COMPLETED, DELIVERED] and old_status in [PACKING, NEW, PAID, READY_TO_SHIP]
            # But order flow is usually linear.
            # User said "Delivered implies cut... Shipping implies cut".
            # Safest trigger: When transitioning TO 'SHIPPED'.
            
            if new_status == "SHIPPED" and old_status != "SHIPPED":
                # Deduct Stock (OUT)
                for item in order.items:
                    StockService.add_stock_movement(db, StockMovementCreate(
                        warehouse_id=order.warehouse_id,
                        product_id=item.product_id,
                        movement_type="OUT",
                        quantity=item.quantity,
                        reference_type="ORDER",
                        reference_id=str(order.id),
                        note=f"Order Shipped: {order.external_order_id}"
                    ), created_by=performed_by, created_at_override=status_changed_at)
            
            # RETURNED -> Return Stock (IN)
            elif new_status == "RETURNED" and old_status != "RETURNED":
                # Add Stock (IN)
                for item in order.items:
                    StockService.add_stock_movement(db, StockMovementCreate(
                        warehouse_id=order.warehouse_id,
                        product_id=item.product_id,
                        movement_type="IN",
                        quantity=item.quantity,
                        reference_type="ORDER",
                        reference_id=str(order.id),
                        note=f"Order Returned: {order.external_order_id}"
                    ), created_by=performed_by, created_at_override=status_changed_at)
                    
        except Exception as e:
            # Log error but don't fail the status update (or should we?)
            # Ideally Transactional, but StockService commits.
            print(f"Error updating stock for order {order.external_order_id}: {e}")
            pass

        return True, "Status updated successfully"
    
    @staticmethod
    def batch_update_status(
        db: Session,
        new_status: str,
        channel: Optional[str] = None,
        current_status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        order_ids: Optional[List[str]] = None,
        performed_by: Optional[UUID] = None
    ) -> Tuple[int, str]:
        """Batch update order status"""
        query = db.query(OrderHeader)
        
        if order_ids:
            # If IDs provided, only update specific orders
            # Filter safe UUIDs
            valid_uuids = []
            external_ids = []
            for oid in order_ids:
                try:
                    valid_uuids.append(UUID(oid))
                except ValueError:
                    external_ids.append(oid)
            
            conditions = []
            if valid_uuids:
                conditions.append(OrderHeader.id.in_(valid_uuids))
            if external_ids:
                conditions.append(OrderHeader.external_order_id.in_(external_ids))
                
            if conditions:
                query = query.filter(or_(*conditions))
            else:
                return 0, "No valid order IDs provided"
        else:
            # Use filters (Same logic as get_orders)
            if start_date or end_date:
                from app.core import settings
                from zoneinfo import ZoneInfo
                from datetime import datetime, timezone
                
                try:
                    tz = ZoneInfo(settings.TIMEZONE)
                except:
                    tz = ZoneInfo("UTC")

                if start_date:
                    s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    s_dt = datetime.combine(s_date, datetime.min.time()).replace(tzinfo=tz)
                    s_dt_utc = s_dt.astimezone(timezone.utc)
                    query = query.filter(OrderHeader.order_datetime >= s_dt_utc)
                    
                if end_date:
                    e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    e_dt = datetime.combine(e_date, datetime.max.time()).replace(tzinfo=tz)
                    e_dt_utc = e_dt.astimezone(timezone.utc)
                    query = query.filter(OrderHeader.order_datetime <= e_dt_utc)
            
            if channel and channel != "all" and channel != "ALL":
                query = query.filter(OrderHeader.channel_code == channel)
            
            if current_status and current_status != "all":
                query = query.filter(OrderHeader.status_normalized == current_status)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        OrderHeader.external_order_id.ilike(search_term),
                        OrderHeader.customer_name.ilike(search_term),
                        OrderHeader.customer_phone.ilike(search_term)
                    )
                )

        orders = query.all()
        count = 0
        errors = 0
        
        for order in orders:
            # Skip if already in status
            if order.status_normalized == new_status:
                continue
                
            success, msg = OrderService.update_status(db, order.id, new_status, performed_by)
            if success:
                count += 1
            else:
                errors += 1
        
        return count, f"Updated {count} orders ({errors} failed/skipped)"
    
    @staticmethod
    def get_dashboard_stats(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        """Get dashboard statistics with optional date range filtering"""
        # Timezone handling
        from app.core import settings
        from zoneinfo import ZoneInfo
        from datetime import timezone, timedelta
        
        try:
            tz = ZoneInfo(settings.TIMEZONE)
        except Exception:
            tz = ZoneInfo("UTC") # Fallback
            
        now = datetime.now(tz)
        today = now.date()
        
        # Determine date range
        if start_date and end_date:
            # Custom range provided
            try:
                filter_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                filter_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except:
                filter_start = today
                filter_end = today
        else:
            # Default to today
            filter_start = today
            filter_end = today
        
        # Convert to UTC for querying
        range_start_local = datetime.combine(filter_start, datetime.min.time()).replace(tzinfo=tz)
        range_end_local = datetime.combine(filter_end, datetime.max.time()).replace(tzinfo=tz)
        range_start_utc = range_start_local.astimezone(timezone.utc)
        range_end_utc = range_end_local.astimezone(timezone.utc)
        
        # Count by status (all time for action items)
        status_counts = db.query(
            OrderHeader.status_normalized,
            func.count(OrderHeader.id)
        ).group_by(OrderHeader.status_normalized).all()
        
        # Orders in selected range
        period_orders = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.order_datetime >= range_start_utc,
            OrderHeader.order_datetime <= range_end_utc
        ).scalar() or 0
        
        # Revenue in selected range
        period_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            OrderHeader.order_datetime >= range_start_utc,
            OrderHeader.order_datetime <= range_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        # Shipped Orders in selected range (based on shipped_at, not order_datetime)
        shipped_orders = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.shipped_at.isnot(None),
            OrderHeader.shipped_at >= range_start_utc,
            OrderHeader.shipped_at <= range_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        # Shipped Revenue in selected range
        shipped_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            OrderHeader.shipped_at.isnot(None),
            OrderHeader.shipped_at >= range_start_utc,
            OrderHeader.shipped_at <= range_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        # Comparison (previous period of same length)
        period_days = (filter_end - filter_start).days + 1
        prev_start = filter_start - timedelta(days=period_days)
        prev_end = filter_end - timedelta(days=period_days)
        
        prev_start_local = datetime.combine(prev_start, datetime.min.time()).replace(tzinfo=tz)
        prev_end_local = datetime.combine(prev_end, datetime.max.time()).replace(tzinfo=tz)
        prev_start_utc = prev_start_local.astimezone(timezone.utc)
        prev_end_utc = prev_end_local.astimezone(timezone.utc)
        
        prev_orders = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.order_datetime >= prev_start_utc,
            OrderHeader.order_datetime <= prev_end_utc
        ).scalar() or 0
        
        prev_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            OrderHeader.order_datetime >= prev_start_utc,
            OrderHeader.order_datetime <= prev_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        
        # Sales Trend (Smart Grouping)
        sales_trend = []
        
        if period_days > 40:
            # Monthly grouping for long periods
            current_date = filter_start.replace(day=1)
            while current_date <= filter_end:
                # Calculate month start and end
                month_start = current_date
                # Find last day of month
                if month_start.month == 12:
                    month_end = month_start.replace(day=31)
                    next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1, day=1)
                    month_end = next_month - timedelta(days=1)
                
                # Clip to filter range
                query_start = max(month_start, filter_start)
                query_end = min(month_end, filter_end)
                
                if query_start <= query_end:
                     d_start = datetime.combine(query_start, datetime.min.time()).replace(tzinfo=tz).astimezone(timezone.utc)
                     d_end = datetime.combine(query_end, datetime.max.time()).replace(tzinfo=tz).astimezone(timezone.utc)
                     
                     month_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
                        OrderHeader.order_datetime >= d_start,
                        OrderHeader.order_datetime <= d_end,
                        OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
                     ).scalar() or 0
                     
                     # Format label: "Jan 2025" or "01/2025"
                     # Thai months abbr
                     thai_months = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
                     month_label = f"{thai_months[current_date.month - 1]} {current_date.year + 543}"
                     
                     sales_trend.append({
                        "date": month_label,
                        "revenue": float(month_revenue)
                     })
                
                current_date = next_month
                
        else:
            # Daily grouping for short periods (existing logic)
            trend_days = period_days # Show all days within period
            # Start from filter_start and go forward
            for i in range(trend_days):
                day_date = filter_start + timedelta(days=i)
                d_start = datetime.combine(day_date, datetime.min.time()).replace(tzinfo=tz).astimezone(timezone.utc)
                d_end = datetime.combine(day_date, datetime.max.time()).replace(tzinfo=tz).astimezone(timezone.utc)
                
                day_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
                    OrderHeader.order_datetime >= d_start,
                    OrderHeader.order_datetime <= d_end,
                    OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
                ).scalar() or 0
                
                sales_trend.append({
                    "date": day_date.strftime("%d/%m"),
                    "revenue": float(day_revenue)
                })
            
        # Channel Stats (for selected period)
        channel_stats = db.query(
            OrderHeader.channel_code,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.order_datetime >= range_start_utc,
            OrderHeader.order_datetime <= range_end_utc
        ).group_by(OrderHeader.channel_code).all()

        # Platform Breakdown (Count + Revenue) - Excluding Cancelled/Returned for Revenue accuracy
        platform_breakdown_query = db.query(
            OrderHeader.channel_code,
            func.count(OrderHeader.id).label("count"),
            func.sum(OrderHeader.total_amount).label("revenue")
        ).filter(
            OrderHeader.order_datetime >= range_start_utc,
            OrderHeader.order_datetime <= range_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).group_by(OrderHeader.channel_code).all()
        
        # Operational Counts (Global - ignoring date range)
        # We want to know pending work regardless of when order came in
        op_counts = db.query(
            OrderHeader.channel_code,
            OrderHeader.status_normalized,
            func.count(OrderHeader.id)
        ).filter(
            OrderHeader.status_normalized.in_(["PAID", "PACKING", "READY_TO_SHIP"])
        ).group_by(
            OrderHeader.channel_code, 
            OrderHeader.status_normalized
        ).all()
        
        # Map op_counts to easy lookup: { 'shopee': {'PAID': 5, 'PACKING': 2}, ... }
        op_map = {}
        for channel, status, count in op_counts:
            if channel not in op_map:
                op_map[channel] = {"paid_count": 0, "packing_count": 0}
            
            # Map status to metric
            # PAID -> paid_count (To Pack)
            # PACKING, READY_TO_SHIP -> packing_count (To Ship / Packing)
            if status == "PAID":
                op_map[channel]["paid_count"] += count
            elif status in ["PACKING", "READY_TO_SHIP"]:
                op_map[channel]["packing_count"] += count
        
        # Merge results
        # We need to ensure we show platforms that might have pending work but NO sales in this period
        all_platforms = set([p.channel_code for p in platform_breakdown_query]) | set(op_map.keys())
        
        # Helper to get sales data
        sales_map = {p.channel_code: {"count": p.count, "revenue": float(p.revenue or 0)} for p in platform_breakdown_query}
        
        platform_breakdown = []
        for platform in all_platforms:
             sales_data = sales_map.get(platform, {"count": 0, "revenue": 0.0})
             op_data = op_map.get(platform, {"paid_count": 0, "packing_count": 0})
             
             platform_breakdown.append({
                 "platform": platform,
                 "count": sales_data["count"],
                 "revenue": sales_data["revenue"],
                 "paid_count": op_data["paid_count"],
                 "packing_count": op_data["packing_count"]
             })
        
        # Sort by revenue desc (optional)
        platform_breakdown.sort(key=lambda x: x["revenue"], reverse=True)
        
        # Top Products (for selected period)
        top_products = db.query(
            OrderItem.sku,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.line_total).label("total_sales")
        ).join(OrderHeader).filter(
            OrderHeader.order_datetime >= range_start_utc,
            OrderHeader.order_datetime <= range_end_utc,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).group_by(OrderItem.sku, OrderItem.product_name)\
         .order_by(func.sum(OrderItem.quantity).desc())\
         .limit(5).all()
        
        return {
            "status_counts": dict(status_counts),
            "period_orders": period_orders,
            "period_revenue": float(period_revenue),
            "shipped_orders": shipped_orders,
            "shipped_revenue": float(shipped_revenue),
            "prev_orders": prev_orders,
            "prev_revenue": float(prev_revenue),
            # Legacy (for backward compat, same as period when no range)
            "today_orders": period_orders,
            "today_revenue": float(period_revenue),
            "mtd_orders": period_orders,
            "mtd_revenue": float(period_revenue),
            "sales_trend": sales_trend,
            "channel_stats": dict(channel_stats),
            "platform_breakdown": platform_breakdown,
            "top_products": [
                {
                    "sku": r.sku,
                    "product_name": r.product_name,
                    "total_qty": r.total_qty,
                    "total_sales": float(r.total_sales)
                } 
                for r in top_products
            ],
            "filter_info": {
                "start_date": filter_start.isoformat(),
                "end_date": filter_end.isoformat(),
                "period_days": period_days
            }
        }

    @staticmethod
    def get_sku_summary(
        db: Session,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[dict]:
        """Get summary of SKUs for orders matching filters"""
        # Query OrderItem joined with OrderHeader
        query = db.query(OrderItem.sku, func.count(OrderItem.id).label('count')) \
            .join(OrderHeader) \
            .filter(OrderItem.sku.isnot(None)) \
            .filter(OrderItem.sku != '')

        # Apply same filters as get_orders
        if start_date or end_date:
            from app.core import settings
            from zoneinfo import ZoneInfo
            from datetime import datetime, timezone
            
            try:
                tz = ZoneInfo(settings.TIMEZONE)
            except:
                tz = ZoneInfo("UTC")

            if start_date:
                s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                s_dt = datetime.combine(s_date, datetime.min.time()).replace(tzinfo=tz)
                s_dt_utc = s_dt.astimezone(timezone.utc)
                query = query.filter(OrderHeader.order_datetime >= s_dt_utc)
                
            if end_date:
                e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                e_dt = datetime.combine(e_date, datetime.max.time()).replace(tzinfo=tz)
                e_dt_utc = e_dt.astimezone(timezone.utc)
                query = query.filter(OrderHeader.order_datetime <= e_dt_utc)
        
        if channel and channel != "all" and channel != "ALL":
            query = query.filter(OrderHeader.channel_code == channel)
        
        if status and status != "all":
            if "," in status:
                status_list = [s.strip() for s in status.split(",")]
                query = query.filter(OrderHeader.status_normalized.in_(status_list))
            else:
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

        # Step 1: Get total quantity per order per SKU (consolidate duplicate rows)
        # This handles cases where TikTok stores same SKU as multiple rows
        from sqlalchemy import literal
        
        # Subquery: sum quantity per order per SKU
        order_sku_qty = db.query(
            OrderItem.order_id,
            OrderItem.sku,
            func.sum(OrderItem.quantity).label('qty_sum')
        ).join(OrderHeader) \
            .filter(OrderItem.sku.isnot(None)) \
            .filter(OrderItem.sku != '')
        
        # Apply status filter
        if status and status != "all":
            if "," in status:
                status_list = [s.strip() for s in status.split(",")]
                order_sku_qty = order_sku_qty.filter(OrderHeader.status_normalized.in_(status_list))
            else:
                order_sku_qty = order_sku_qty.filter(OrderHeader.status_normalized == status)
        
        if channel and channel != "all" and channel != "ALL":
            order_sku_qty = order_sku_qty.filter(func.lower(OrderHeader.channel_code) == channel.lower())
        
        if search:
            search_term = f"%{search}%"
            order_sku_qty = order_sku_qty.filter(
                or_(
                    OrderHeader.external_order_id.ilike(search_term),
                    OrderHeader.customer_name.ilike(search_term),
                    OrderHeader.customer_phone.ilike(search_term)
                )
            )
        
        # Group by order + SKU to get consolidated qty per order
        order_sku_results = order_sku_qty.group_by(OrderItem.order_id, OrderItem.sku).all()
        
        # Step 2: Aggregate into per-SKU summaries with qty breakdown
        sku_data = {}
        for order_id, sku, qty_sum in order_sku_results:
            qty_sum = int(qty_sum) if qty_sum else 1
            
            if sku not in sku_data:
                sku_data[sku] = {
                    "sku": sku,
                    "count": 0,
                    "total_qty": 0,
                    "qty_1": 0,
                    "qty_2": 0,
                    "qty_3_plus": 0
                }
            
            # Each row here = 1 order (since we grouped by order_id, sku)
            sku_data[sku]["count"] += 1
            sku_data[sku]["total_qty"] += qty_sum
            
            # Breakdown by consolidated quantity
            if qty_sum == 1:
                sku_data[sku]["qty_1"] += 1
            elif qty_sum == 2:
                sku_data[sku]["qty_2"] += 1
            else:
                sku_data[sku]["qty_3_plus"] += 1
        
        # Sort by count descending
        sorted_skus = sorted(sku_data.values(), key=lambda x: x["count"], reverse=True)
        return sorted_skus

    @staticmethod
    async def batch_arrange_shipment(
        db: Session,
        order_ids: List[str]
    ) -> tuple[int, List[dict]]:
        """
        Arrange shipment (RTS) for multiple orders.
        Returns (success_count, results_list)
        """
        from app.services import integration_service
        from app.integrations.tiktok import TikTokClient
        
        results = []
        success_count = 0
        
        # Cache clients
        client_cache = {}
        
        for order_id_str in order_ids:
            try:
                # 1. Get Order
                try:
                    uuid_obj = UUID(order_id_str)
                    order = OrderService.get_order_by_id(db, uuid_obj)
                except ValueError:
                    order = OrderService.get_order_by_external_id(db, order_id_str)
                
                if not order:
                    results.append({"id": order_id_str, "success": False, "message": "Order not found"})
                    continue
                
                if order.channel_code.lower() != 'tiktok':
                    results.append({"id": order_id_str, "success": False, "message": f"Platform {order.channel_code} not supported"})
                    continue
                
                # 2. Get Client
                if 'tiktok' not in client_cache:
                    configs = integration_service.get_platform_configs(db, platform='tiktok', is_active=True)
                    if not configs:
                        results.append({"id": order_id_str, "success": False, "message": "No active TikTok config"})
                        continue
                    client_cache['tiktok'] = integration_service.get_client_for_config(configs[0])
                
                client = client_cache['tiktok']
                if not isinstance(client, TikTokClient):
                    results.append({"id": order_id_str, "success": False, "message": "Client error"})
                    continue

                # 3. Get Package ID via Order Detail
                # We need fresh detail from API to get package ID
                order_detail = await client.get_order_detail(order.external_order_id)
                packages = order_detail.get("packages", [])
                if not packages:
                    results.append({"id": order_id_str, "success": False, "message": "No packages found"})
                    continue
                
                package_id = packages[0].get("id")
                
                # 4. Ship Package
                # Default to DROP_OFF for now
                await client.ship_package(package_id, handover_method="DROP_OFF")
                
                # 5. Update Local Status
                # "AWAITING_COLLECTION" is normalized to "PACKING" or "SHIPPED"?
                # "Awaiting Collection" maps to "READY_TO_SHIP" in Shopee, usually "PACKING" in our system?
                # Actually, if we RTS, strict status is "Ready to Ship".
                # Update local DB status if desired?
                # Let's verify status from API or just set to PACKING?
                # User flow: Paid -> RTS -> Print -> Pack.
                # If we RTS, it stays in 'PAID' list unless we change status?
                # Packing page filters for 'PAID'.
                # In TikTok: 'Awaiting Shipment' -> 'Awaiting Collection'.
                # Our normalization: 'PAID' covers both?
                # Let's check status map in tiktok.py:
                # 'AWAITING_COLLECTION' -> 'PAID'?
                # If it stays 'PAID', it stays on screen.
                # If user workflow is RTS -> Print -> Mark as Packed (which moves to PACKING status),
                # Then we SHOULD NOT change status here, just RTS API call.
                
                results.append({"id": order_id_str, "success": True, "message": "Success"})
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to RTS order {order_id_str}: {e}")
                results.append({"id": order_id_str, "success": False, "message": str(e)})
        
        return success_count, results

