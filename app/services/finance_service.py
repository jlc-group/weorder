from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Dict, Any

from app.models import OrderHeader, PaymentReceipt

class FinanceService:
    """Finance specific business logic"""
    
    @staticmethod
    def get_finance_summary(db: Session) -> Dict[str, Any]:
        """Get finance summary dashboard data"""
        today = datetime.now().date()
        
        # 1. Today's Revenue (Sum of total_amount for PAID orders with order_datetime today)
        today_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            func.date(OrderHeader.order_datetime) == today,
            OrderHeader.payment_status == 'PAID'
        ).scalar() or 0
        
        # 2. Paid Orders Count (Today)
        paid_today = db.query(func.count(OrderHeader.id)).filter(
            func.date(OrderHeader.order_datetime) == today,
            OrderHeader.payment_status == 'PAID'
        ).scalar() or 0
        
        # Count Pending (Total backlog)
        pending_count = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.payment_status == 'PENDING',
            OrderHeader.status_normalized != 'CANCELLED'
        ).scalar() or 0
        
        # 3. Recent Transactions (From PaymentReceipt)
        transactions = db.query(PaymentReceipt).order_by(
            PaymentReceipt.created_at.desc()
        ).limit(10).all()
        
        return {
            "today_revenue": float(today_revenue),
            "paid_today": paid_today,
            "pending_count": pending_count,
            "transactions": [
                {
                    "id": str(t.id),
                    "created_at": t.created_at.isoformat(),
                    "amount": float(t.amount),
                    "method": t.payment_method,
                    "status": t.status,
                    "note": t.note
                }
                for t in transactions
            ]
        }
    @staticmethod
    def get_performance_dashboard(db: Session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get aggregated performance data for a specific date range.
        Calculates revenue, fees, income, and COGS.
        """
        from app.models.finance import MarketplaceTransaction
        from app.models import OrderHeader, OrderItem, Product
        from sqlalchemy import and_

        # 1. Aggregated Transactions from MarketplaceTransaction
        # Using MarketplaceTransaction as the source of truth for platform revenue and fees
        tx_query = db.query(
            MarketplaceTransaction.platform,
            MarketplaceTransaction.transaction_type,
            func.sum(MarketplaceTransaction.amount).label("total_amount")
        ).filter(
            MarketplaceTransaction.transaction_date >= start_date,
            MarketplaceTransaction.transaction_date <= end_date
        ).group_by(
            MarketplaceTransaction.platform,
            MarketplaceTransaction.transaction_type
        ).all()

        # Organize data by platform and type
        platform_data = {}
        total_revenue = 0
        total_fees = 0
        
        fee_types = ['COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 'PAYMENT_FEE', 'SHIPPING_FEE', 'ADJUSTMENT']

        for plat, tx_type, amount in tx_query:
            if plat not in platform_data:
                platform_data[plat] = {
                    "revenue": 0,
                    "fees": 0,
                    "fee_details": {},
                    "net_income": 0,
                    "cogs": 0
                }
            
            amt = float(amount or 0)
            
            # Revenue calculation (ITEM_PRICE is usually positive)
            if tx_type == 'ITEM_PRICE':
                platform_data[plat]["revenue"] += amt
                total_revenue += amt
            
            # Fees calculation (Usually negative from platform)
            elif tx_type in fee_types:
                platform_data[plat]["fees"] += amt # This is usually -ve
                platform_data[plat]["fee_details"][tx_type] = amt
                total_fees += amt

        # 2. Calculate COGS for orders in this period
        # We look at orders shipped/ordered in this period
        cogs_query = db.query(
            OrderHeader.channel_code,
            func.sum(OrderItem.quantity * Product.standard_cost).label("total_cogs")
        ).join(OrderItem, OrderHeader.id == OrderItem.order_id)\
         .join(Product, OrderItem.product_id == Product.id)\
         .filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime <= end_date,
            OrderHeader.status_normalized != 'CANCELLED'
        ).group_by(OrderHeader.channel_code).all()

        total_cogs = 0
        for channel, cogs_val in cogs_query:
            plat = channel.lower() if channel else "unknown"
            if plat in platform_data:
                cogs_amt = float(cogs_val or 0)
                platform_data[plat]["cogs"] = cogs_amt
                total_cogs += cogs_amt

        # 2a. FIX: Fetch TikTok Aggregates from raw_data (JSONB)
        # TikTok transactions are stored as "ORDER" with net settlement. 
        # We need to extract 'revenue_amount' and 'fee_amount' from raw_data for true financials.
        try:
            from sqlalchemy import text
            tiktok_stats = db.execute(text("""
                SELECT 
                    SUM(CAST(raw_data->>'revenue_amount' AS NUMERIC)) as revenue,
                    SUM(CAST(raw_data->>'fee_amount' AS NUMERIC)) as fees
                FROM marketplace_transaction
                WHERE platform = 'tiktok' 
                  AND transaction_type = 'ORDER'
                  AND transaction_date >= :start_date 
                  AND transaction_date <= :end_date
            """), {"start_date": start_date, "end_date": end_date}).first()

            if tiktok_stats and tiktok_stats.revenue:
                tk_rev = float(tiktok_stats.revenue or 0)
                tk_fees = float(tiktok_stats.fees or 0)
                
                if "tiktok" not in platform_data:
                    platform_data["tiktok"] = {
                        "revenue": 0,
                        "fees": 0,
                        "fee_details": {},
                        "net_income": 0,
                        "cogs": 0
                    }
                
                # So we can safely ADD these values.
                platform_data["tiktok"]["revenue"] += tk_rev
                platform_data["tiktok"]["fees"] += tk_fees # fees are negative
                
                # Add overall fees to summary
                total_revenue += tk_rev
                total_fees += tk_fees

        except Exception as e:
            print(f"Error fetching TikTok raw stats: {e}")

        # Finalize platform stats
        results_list = []
        for plat, data in platform_data.items():
            data["platform"] = plat
            # Net income from platform = Revenue - Abs(Fees)
            # Since fees are negative, we add them
            data["net_income"] = data["revenue"] + data["fees"]
            # Net margin = Net Income - COGS
            data["net_profit"] = data["net_income"] - data["cogs"]
            results_list.append(data)

        # 3. Monthly Trend (Past 30 days)
        # TODO: Implement trend query if needed

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_revenue": total_revenue,
                "total_fees": total_fees,
                "total_net_income": total_revenue + total_fees,
                "total_cogs": total_cogs,
                "total_net_profit": (total_revenue + total_fees) - total_cogs
            },
            "platforms": results_list
        }
