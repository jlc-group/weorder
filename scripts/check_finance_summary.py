
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.finance import MarketplaceTransaction
from datetime import datetime

def check_finance_summary():
    session = SessionLocal()
    try:
        print("Querying finance summary from database...")
        
        # Group by Platform, Year, Month
        result = (
            session.query(
                MarketplaceTransaction.platform,
                func.extract('year', MarketplaceTransaction.transaction_date).label('year'),
                func.extract('month', MarketplaceTransaction.transaction_date).label('month'),
                func.count(MarketplaceTransaction.id).label('count'),
                func.sum(MarketplaceTransaction.amount).label('total_amount'),
                func.min(MarketplaceTransaction.transaction_date).label('first_date'),
                func.max(MarketplaceTransaction.transaction_date).label('last_date')
            )
            .filter(MarketplaceTransaction.transaction_date >= datetime(2025, 1, 1))
            .filter(MarketplaceTransaction.transaction_type != 'STATEMENT_SUMMARY') # Exclude summaries
            .group_by(
                MarketplaceTransaction.platform,
                func.extract('year', MarketplaceTransaction.transaction_date),
                func.extract('month', MarketplaceTransaction.transaction_date)
            )
            .order_by(
                MarketplaceTransaction.platform,
                func.extract('year', MarketplaceTransaction.transaction_date),
                func.extract('month', MarketplaceTransaction.transaction_date)
            )
            .all()
        )
        
        print("\n=== Finance Sync Summary (2025-Present) ===")
        # Header
        print(f"{'Platform':<10} | {'Month':<7} | {'Transactions':>12} | {'Net Amount':>15} | {'First Date':<10} | {'Last Date':<10}")
        print("-" * 85)
        
        total_tx = 0
        total_amt = 0.0
        
        for row in result:
            amt = float(row.total_amount) if row.total_amount else 0.0
            print(f"{row.platform.upper():<10} | {int(row.year)}-{int(row.month):02d}   | {row.count:>12,} | {amt:>15,.2f} | {row.first_date.strftime('%Y-%m-%d') if row.first_date else 'N/A'} | {row.last_date.strftime('%Y-%m-%d') if row.last_date else 'N/A'}")
            total_tx += row.count
            total_amt += amt
            
        print("-" * 85)
        print(f"{'TOTAL':<10} | {'ALL':<7} | {total_tx:>12,} | {total_amt:>15,.2f} | {'':<10} | {'':<10}")

    finally:
        session.close()

if __name__ == "__main__":
    check_finance_summary()
