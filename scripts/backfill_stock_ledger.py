
import sys
import os
from datetime import datetime
from uuid import UUID

# Setup Path
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models import OrderHeader, OrderItem, StockLedger, Product
from app.services.stock_service import StockService
from app.schemas.stock import StockMovementCreate

def backfill():
    db = SessionLocal()
    try:
        print("--- Backfilling Stock Ledger ---")
        
        # 1. Find Orders that are Shipped/Completed but have NO Stock Ledger entry
        # Status "OUT" implies: SHIPPED, COMPLETED, DELIVERED, PACKED(Maybe?)
        # Let's stick to SHIPPED+
        target_statuses = ["SHIPPED", "COMPLETED", "DELIVERED", "READY_TO_SHIP"]
        
        # Get all orders in these statuses
        # Optimization: Filter by date if needed? Or all time?
        # Let's do all time.
        
        
        # 1. Get all Target Order IDs first to avoid Cursor invalidation during commit
        print("Fetching Order IDs...")
        order_ids = [
            oid for oid, in db.query(OrderHeader.id).filter(
                OrderHeader.status_normalized.in_(target_statuses)
            ).all()
        ]
        total_orders = len(order_ids)
        print(f"Found {total_orders} candidate orders. Starting backfill...")
        
        # Cache Warehouse ID (Default)
        default_warehouse_id = None
        from app.models import Warehouse
        wh = db.query(Warehouse).first()
        if wh:
            default_warehouse_id = wh.id
            print(f"Using Default Warehouse: {wh.name} ({wh.id})")
        
        count = 0
        skipped = 0
        error_count = 0
        
        for i, oid in enumerate(order_ids):
            try:
                # Fetch fresh order object
                order = db.query(OrderHeader).get(oid)
                if not order: continue

                # Check if ledger exists
                exists = db.query(StockLedger).filter(
                    StockLedger.reference_id == str(oid),
                    StockLedger.reference_type == "ORDER",
                    StockLedger.movement_type == "OUT"
                ).first()
                
                if exists:
                    skipped += 1
                    continue
                
                # Use order_datetime (Order Time) or fallback
                date_to_use = order.order_datetime or datetime.now()
                
                # Determine Warehouse
                warehouse_id = order.warehouse_id
                if not warehouse_id:
                     warehouse_id = default_warehouse_id
                
                if not warehouse_id:
                     error_count += 1
                     continue # Cannot create without warehouse

                items_added = 0
                for item in order.items:
                     pid = item.product_id
                     
                     # If no product_id, try to resolve by SKU
                     if not pid and item.sku:
                         prod = db.query(Product).filter(Product.sku == item.sku).first()
                         if prod:
                             pid = prod.id
                             # Optional: Fix OrderItem? db.add(item); item.product_id = pid
                     
                     if not pid:
                         # Still no Product ID, cannot track stock
                         continue

                     movement = StockLedger(
                        warehouse_id=warehouse_id,
                        product_id=pid,
                        movement_type="OUT",
                        quantity=item.quantity,
                        reference_type="ORDER",
                        reference_id=str(order.id),
                        note=f"Backfill: {order.external_order_id}",
                        created_at=date_to_use
                    )
                     db.add(movement)
                     items_added += 1
                
                if items_added > 0:
                    count += 1
                else:
                    skipped += 1 # No items valid
                
                if count % 10 == 0 and count > 0:
                    db.commit()
                    print(f"Processed {count} orders (Skipped: {skipped}, Errors: {error_count})...")
            
            except Exception as e:
                db.rollback() # Rollback standard transaction if failed
                error_count += 1
                print(f"Error processing order {oid}: {e}")
                continue
                
        db.commit() # Final commit
        print(f"Done. Backfilled {count} orders. Skipped {skipped}. Errors {error_count}.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
