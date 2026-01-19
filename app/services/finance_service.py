from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc, case
from datetime import datetime
from typing import Dict, Any

from app.models import OrderHeader, PaymentReceipt

class FinanceService:
    """Finance specific business logic"""
    
    @staticmethod
    def get_finance_summary(db: Session) -> Dict[str, Any]:
        """Get finance summary dashboard data"""
        today = datetime.now().date()
        
        # 1. Today's Cash Revenue (Customer Paid)
        # Sum of total_amount for PAID orders with order_datetime today
        today_cash_revenue = db.query(func.sum(OrderHeader.total_amount)).filter(
            func.date(OrderHeader.order_datetime) == today,
            OrderHeader.payment_status == 'PAID'
        ).scalar() or 0

        # 2. Today's Tax Revenue (Gross Revenue including Platform Subsidy & Shipping Subsidy)
        # Sum of (total_amount + platform_discount_amount + shipping_fee_platform_discount)
        today_gross_revenue = db.query(
            func.sum(
                OrderHeader.total_amount + 
                func.coalesce(OrderHeader.platform_discount_amount, 0) + 
                func.coalesce(OrderHeader.shipping_fee_platform_discount, 0)
            )
        ).filter(
            func.date(OrderHeader.order_datetime) == today,
            OrderHeader.payment_status == 'PAID'
        ).scalar() or 0
        
        # 3. Paid Orders Count (Today)
        paid_today = db.query(func.count(OrderHeader.id)).filter(
            func.date(OrderHeader.order_datetime) == today,
            OrderHeader.payment_status == 'PAID'
        ).scalar() or 0
        
        # Count Pending (Total backlog)
        pending_count = db.query(func.count(OrderHeader.id)).filter(
            OrderHeader.payment_status == 'PENDING',
            OrderHeader.status_normalized != 'CANCELLED'
        ).scalar() or 0
        
        # 4. Recent Transactions (From PaymentReceipt)
        transactions = db.query(PaymentReceipt).order_by(
            PaymentReceipt.created_at.desc()
        ).limit(10).all()
        
        return {
            "today_revenue": float(today_cash_revenue),     # Legacy field (Keep for compatibility)
            "today_cash_revenue": float(today_cash_revenue),
            "today_gross_revenue": float(today_gross_revenue), # New Tax Base field
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
    def get_order_profitability(db: Session, start_date: datetime, end_date: datetime):
        from app.models import OrderHeader, OrderItem, Product
        from app.models.finance import MarketplaceTransaction
        from sqlalchemy.orm import joinedload
        
        # ORM Query (SQLite Friendly)
        orders = db.query(OrderHeader).options(
            joinedload(OrderHeader.items).joinedload(OrderItem.product)
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime <= end_date
        ).order_by(desc(OrderHeader.order_datetime)).limit(2000).all()
        
        # Pre-fetch all fees for these orders in one query (batch)
        order_ids = [o.id for o in orders]
        
        # Query actual fees from MarketplaceTransaction
        fee_query = db.query(
            MarketplaceTransaction.order_id,
            func.sum(MarketplaceTransaction.amount).label("total_fees")
        ).filter(
            MarketplaceTransaction.order_id.in_(order_ids),
            MarketplaceTransaction.transaction_type.in_([
                'COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 
                'PAYMENT_FEE', 'SHIPPING_FEE'
            ])
        ).group_by(MarketplaceTransaction.order_id).all()
        
        # Create lookup map: order_id -> actual fees (negative values = deductions)
        actual_fees_map = {str(order_id): float(total_fees or 0) for order_id, total_fees in fee_query}

        results = []
        for o in orders:
            # Calculate COGS
            order_cogs = 0
            items_desc = []
            
            for item in o.items:
                # Find cost: item.product.standard_cost/cost_price
                # Fallback to 0 if not found
                cost = 0
                if item.product:
                    cost = float(item.product.standard_cost or 0)
                
                qty = item.quantity or 0
                item_cogs = cost * qty
                order_cogs += item_cogs
                
                items_desc.append(f"{item.sku} x{qty}")

            revenue = float(o.total_amount or 0)
            
            # Get actual fees from MarketplaceTransaction if available
            actual_fees = actual_fees_map.get(str(o.id))
            if actual_fees is not None:
                # actual_fees is typically negative (deductions), so we take abs value
                fees = abs(actual_fees)
                fees_source = "actual"
            else:
                # Fallback to estimate 12% if no transaction data
                fees = revenue * 0.12
                fees_source = "estimate"
            
            # Net Profit
            net_profit = revenue - fees - order_cogs
            margin = (net_profit / revenue * 100) if revenue > 0 else 0

            results.append({
                "order_number": o.external_order_id,
                "platform": o.channel_code,
                "date": o.order_datetime.strftime('%Y-%m-%d') if o.order_datetime else "",
                "items": ", ".join(items_desc),
                "revenue": revenue,
                "cogs": order_cogs,
                "fees": fees,
                "fees_source": fees_source,  # New field: "actual" or "estimate"
                "net_profit": net_profit,
                "margin_percent": margin
            })
            
        return results

    @staticmethod
    def get_performance_dashboard(db: Session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get finance performance with Reconciliation View (Tax vs Cash) and True Profit.
        """
        from app.models.finance import MarketplaceTransaction, InternalExpense
        from app.models import OrderHeader, OrderItem, Product
        from sqlalchemy import and_, text

        # --- 1. Internal Expenses (Company Side) ---
        internal_expenses = db.query(InternalExpense).filter(
            InternalExpense.expense_date >= start_date,
            InternalExpense.expense_date <= end_date
        ).all()
        
        total_internal_expense = sum(float(e.amount or 0) for e in internal_expenses)

        # --- 2. COGS Calculation (Product Cost) ---
        # Based on Orders placed in this period (Tax Base match)
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

        cogs_map = {}
        total_cogs_ex_vat = 0
        total_cogs_inc_vat = 0

        for channel, cogs_val in cogs_query:
            plat = channel.lower() if channel else "unknown"
            cogs_amt = float(cogs_val or 0)
            cogs_map[plat] = cogs_amt
            total_cogs_ex_vat += cogs_amt
            total_cogs_inc_vat += (cogs_amt * 1.07) # Assuming 7% VAT

        # --- 3. Platform Data Structure Update ---
        platform_data = {}
        platforms = ['shopee', 'tiktok', 'lazada', 'line_shopping', 'manual']
        
        for p in platforms:
            platform_data[p] = {
                "product_sales": 0,     # Pure Goods Sales
                "shipping_income": 0,   # Paid by Customer
                "tax_revenue": 0,       # Total Tax Base (Sales + Ship Income)
                
                "platform_fees": 0,     # Comm/Trans/Service Fees
                "shipping_cost": 0,     # Deducted by Platform
                "cash_fees": 0,         # Total Deductions (Fees + Ship Cost)
                
                "cash_payout": 0,       # Actual Bank Transfer
                
                "cogs_ex_vat": cogs_map.get(p, 0),
                "cogs_inc_vat": cogs_map.get(p, 0) * 1.07,
                "net_profit_tax": 0
            }

        # 3.1 Fetch Data (Unified MarketplaceTransaction)
        
        # A. TikTok Logic (JSONB Extraction)
        try:
            tiktok_stats = db.execute(text("""
                SELECT 
                    SUM(CAST(raw_data->>'gross_sales_amount' AS NUMERIC)) as gross_sales,
                    SUM(CAST(raw_data->>'customer_paid_shipping_fee_amount' AS NUMERIC)) as shipping_paid,
                    SUM(CAST(raw_data->>'fee_amount' AS NUMERIC)) as fees,
                    SUM(CAST(raw_data->>'shipping_fee_amount' AS NUMERIC)) as shipping_cost_deduction,
                    SUM(CAST(raw_data->>'settlement_amount' AS NUMERIC)) as settlement
                FROM marketplace_transaction
                WHERE platform = 'tiktok' 
                  AND transaction_type = 'ORDER'
                  AND transaction_date >= :start_date 
                  AND transaction_date <= :end_date
            """), {"start_date": start_date, "end_date": end_date}).first()
            
            if tiktok_stats:
                # Revenue Side
                prod_sales = float(tiktok_stats.gross_sales or 0)
                ship_inc = float(tiktok_stats.shipping_paid or 0)
                
                platform_data['tiktok']['product_sales'] = prod_sales
                platform_data['tiktok']['shipping_income'] = ship_inc
                platform_data['tiktok']['tax_revenue'] = prod_sales + ship_inc
                
                # Expense Side (Fees are negative in DB usually? TikTok 'fee_amount' is negative)
                # 'fee_amount' in TikTok usually INCLUDES shipping_fee if deducted. 
                # We need to check if 'shipping_fee_amount' is overlapping.
                # Standard TikTok: fee_amount = comm + tx + shipping + adjustments.
                # To split, we rely on 'shipping_fee_amount' (usually negative).
                
                total_fees_blob = float(tiktok_stats.fees or 0)
                ship_cost_deduct = float(tiktok_stats.shipping_cost_deduction or 0)
                
                # If ship_cost is part of fees, we split it out
                # But 'fee_amount' sum is the master deduction. 
                # Let's assume fee_amount is the TOTAL deduction.
                # plat_fee = total_fees - ship_cost
                
                platform_data['tiktok']['shipping_cost'] = ship_cost_deduct
                platform_data['tiktok']['platform_fees'] = total_fees_blob - ship_cost_deduct
                platform_data['tiktok']['cash_fees'] = total_fees_blob # Sum of both
                
                platform_data['tiktok']['cash_payout'] = float(tiktok_stats.settlement or 0) 
                
        except Exception as e:
            print(f"Error TikTok Stats: {e}")

        # B. General (Shopee/Others) - Try MarketplaceTransaction first
        tx_query = db.query(
            MarketplaceTransaction.platform,
            MarketplaceTransaction.transaction_type,
            func.sum(MarketplaceTransaction.amount)
        ).filter(
            MarketplaceTransaction.platform != 'tiktok',
            MarketplaceTransaction.transaction_date >= start_date,
            MarketplaceTransaction.transaction_date <= end_date
        ).group_by(MarketplaceTransaction.platform, MarketplaceTransaction.transaction_type).all()

        for plat, tx_type, amount in tx_query:
            if plat not in platform_data: continue
            amt = float(amount or 0)
            
            if tx_type == 'ITEM_PRICE':
                platform_data[plat]['product_sales'] += amt
                platform_data[plat]['tax_revenue'] += amt
                
            elif tx_type == 'SHIPPING_INCOME':
                 platform_data[plat]['shipping_income'] += amt
                 platform_data[plat]['tax_revenue'] += amt
                 
            elif tx_type == 'SHIPPING_FEE':
                 # This is the cost deducted
                 platform_data[plat]['shipping_cost'] += amt
                 platform_data[plat]['cash_fees'] += amt
                 
            elif tx_type in ['COMMISSION_FEE', 'SERVICE_FEE', 'TRANSACTION_FEE', 'PAYMENT_FEE']:
                platform_data[plat]['platform_fees'] += amt
                platform_data[plat]['cash_fees'] += amt
                
            elif tx_type == 'ESCROW_RELEASE' or tx_type == 'WITHDRAWAL':
                platform_data[plat]['cash_payout'] += amt

        # C. Fallback: Use OrderHeader for platforms without MarketplaceTransaction
        # Query revenue from Orders directly
        order_revenue_query = db.query(
            OrderHeader.channel_code,
            func.sum(OrderHeader.total_amount).label("revenue"),
            func.sum(OrderHeader.shipping_fee).label("shipping_income")
        ).filter(
            OrderHeader.order_datetime >= start_date,
            OrderHeader.order_datetime <= end_date,
            OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED'])
        ).group_by(OrderHeader.channel_code).all()

        for channel, revenue, ship_income in order_revenue_query:
            plat = channel.lower() if channel else "unknown"
            if plat not in platform_data:
                continue
            
            rev = float(revenue or 0)
            ship = float(ship_income or 0)
            
            # Only use fallback if MarketplaceTransaction data is missing
            if platform_data[plat]['product_sales'] == 0 and rev > 0:
                platform_data[plat]['product_sales'] = rev - ship
                platform_data[plat]['shipping_income'] = ship
                platform_data[plat]['tax_revenue'] = rev
                
                # Estimate fees at 12% if no transaction data
                est_fees = rev * 0.12
                platform_data[plat]['platform_fees'] = -est_fees
                platform_data[plat]['cash_fees'] = -est_fees

        # --- 4. Final Aggregation ---
        total_product_sales = sum(p['product_sales'] for p in platform_data.values())
        total_shipping_income = sum(p['shipping_income'] for p in platform_data.values())
        total_tax_revenue = sum(p['tax_revenue'] for p in platform_data.values())
        
        total_platform_fees = sum(p['platform_fees'] for p in platform_data.values())
        total_shipping_cost = sum(p['shipping_cost'] for p in platform_data.values())
        total_cash_fees = sum(p['cash_fees'] for p in platform_data.values())
        
        # Net Profit (Tax Base) = Revenue - Fees - COGS(ExVAT)
        total_gross_profit = total_tax_revenue + total_cash_fees - total_cogs_ex_vat
        
        # True Net Profit = Gross Profit - Internal Expenses
        true_net_profit = total_gross_profit - total_internal_expense
        
        # Format Platforms list
        results_list = []
        for plat, data in platform_data.items():
            data["platform"] = plat
            data["net_profit_tax"] = data["tax_revenue"] + data["cash_fees"] - data["cogs_ex_vat"]
            results_list.append(data)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_product_sales": total_product_sales,
                "total_shipping_income": total_shipping_income,
                "total_tax_revenue": total_tax_revenue,
                
                "total_cogs_ex_vat": total_cogs_ex_vat,
                "total_cogs_inc_vat": total_cogs_inc_vat,
                
                "total_platform_fees": total_platform_fees,
                "total_shipping_cost": total_shipping_cost,
                "total_fees": total_cash_fees,
                
                "gross_profit": total_gross_profit,
                "total_internal_expense": total_internal_expense,
                "true_net_profit": true_net_profit
            },
            "internal_expenses": [
                {
                    "title": e.title,
                    "amount": float(e.amount),
                    "category": e.category,
                    "date": e.expense_date.isoformat()
                } for e in internal_expenses
            ],
            "platforms": results_list
        }
