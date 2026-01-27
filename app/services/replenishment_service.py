"""
Replenishment Service
Handles logic for Smart Reorder System:
- Calculate Sales Velocity (Avg sales per day)
- Estimate Days of Inventory Remaining
- Suggest Reorder Quantities
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID

from app.models import Product, OrderHeader, OrderItem, StockBalance

class ReplenishmentService:
    
    @staticmethod
    def get_sales_velocity(db: Session, product_id: UUID, days: int = 30) -> float:
        """
        Calculate Average Daily Sales (ADS) over the last X days.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Query total quantity sold in period
        # Exclude Cancelled/Returned
        total_sold = db.query(func.sum(OrderItem.quantity)).join(OrderHeader).filter(
            OrderItem.product_id == product_id,
            OrderHeader.order_datetime >= start_date,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).scalar() or 0
        
        # Velocity = Total Sold / Days
        return float(total_sold) / days

    @staticmethod
    def get_replenishment_plan(db: Session, days_lookback: int = 30) -> List[Dict]:
        """
        Generate a replenishment plan for all active products.
        Returns detailed stats for each product.
        """
        # 1. Get all active products
        products = db.query(Product).filter(Product.is_active == True).all()
        
        plan = []
        
        # Optimization: Pre-fetch stock balances (summarized by product)
        stock_map = {}
        stock_query = db.query(
            StockBalance.product_id, 
            func.sum(StockBalance.quantity).label('total_qty')
        ).group_by(StockBalance.product_id).all()
        
        for pid, qty in stock_query:
            stock_map[pid] = qty or 0
            
        # Optimization: Pre-fetch sales data for all products in one go?
        # For now, simplistic loop might be slow if 1000s of products.
        # Let's use a single query for velocity to be efficient.
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_lookback)
        
        sales_query = db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(OrderHeader).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.status_normalized.notin_(["CANCELLED", "RETURNED"])
        ).group_by(OrderItem.product_id).all()
        
        sales_map = {r.product_id: (r.total_sold or 0) for r in sales_query}
        
        for p in products:
            # 1. Current Stock
            current_stock = stock_map.get(p.id, 0)
            
            # 2. Sales Velocity (Avg/Day)
            total_sold_period = sales_map.get(p.id, 0)
            velocity = float(total_sold_period) / days_lookback
            
            # 3. Days Remaining
            # If velocity is 0, days remaining is Infinite (999)
            if velocity > 0:
                days_remaining = int(current_stock / velocity)
            else:
                days_remaining = 999
            
            # 4. Target Stock
            # Target Qty = Velocity * Target Days
            target_days = p.target_days_to_keep or 30
            target_stock = velocity * target_days
            
            # 5. Suggested Order
            # Suggest = Target - Current (if < ReorderPoint logic? or just enforce Target?)
            # Smart Logic: If Stock is projected to run out soon?
            # Simple Logic: Fill up to Target.
            suggested_qty = int(target_stock - current_stock)
            
            # Don't suggest negative
            if suggested_qty < 0:
                suggested_qty = 0
                
            # Status Flag
            status = "OK"
            if current_stock <= (p.reorder_point or 0):
                status = "LOW_STOCK" # Below absolute minimum
            elif days_remaining < (p.lead_time_days or 7):
                status = "CRITICAL" # Will run out before new stock arrives
            elif suggested_qty > 0:
                status = "REORDER" # Below target
            
            plan.append({
                "product_id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "image_url": p.image_url,
                "current_stock": current_stock,
                "velocity_per_day": round(velocity, 2),
                "sales_30d": int(total_sold_period),
                "days_remaining": days_remaining,
                "target_days": target_days,
                "suggested_qty": suggested_qty,
                "status": status,
                "lead_time_days": p.lead_time_days
            })
            
        # Sort by urgency: CRITICAL -> LOW_STOCK -> REORDER -> OK
        priority_map = {"CRITICAL": 0, "LOW_STOCK": 1, "REORDER": 2, "OK": 3}
        plan.sort(key=lambda x: priority_map[x["status"]])
        
        return plan
