
import sys
import os
from uuid import uuid4
from datetime import datetime
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
try:
    from app.core import settings
    # Import specific models
    from app.models.master import Company, Warehouse, SalesChannel
    from app.models.product import Product, ProductSetBom
    from app.models.order import OrderHeader, OrderItem
    from app.models.stock import StockLedger
    from app.models.mapping import PlatformListingItem
    from app.services.stock_service import StockService
except ImportError:
    pass

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def cleanup():
    print("Cleaning up old test data...")
    try:
        # 1. Find Test Products
        test_products = db.query(Product).filter(Product.sku.like("TEST_%")).all()
        pids = [p.id for p in test_products]
        
        if pids:
            # Delete referencing Platform Listing Items
            db.query(PlatformListingItem).filter(PlatformListingItem.product_id.in_(pids)).delete(synchronize_session=False)
            db.commit() # Force commit to ensure references are gone

            # Delete StockLedger
            db.query(StockLedger).filter(StockLedger.product_id.in_(pids)).delete(synchronize_session=False)
            # Delete ProductSetBom
            db.query(ProductSetBom).filter(
                (ProductSetBom.set_product_id.in_(pids)) | 
                (ProductSetBom.component_product_id.in_(pids))
            ).delete(synchronize_session=False)
            # Delete OrderItems
            db.query(OrderItem).filter(OrderItem.product_id.in_(pids)).delete(synchronize_session=False)
            
            # Delete Products
            db.query(Product).filter(Product.id.in_(pids)).delete(synchronize_session=False)
            
        db.commit()
        print("Cleanup done.")
    except Exception as e:
        db.rollback()
        print(f"Cleanup Failed: {e}")
        raise e

def test_current_logic():
    cleanup()
    print("--- Testing Current Bundle Logic ---")
    
    # 1. Setup Data
    # Warehouse
    wh = db.query(Warehouse).first()
    if not wh:
        print("No warehouse found!")
        return

    # Company
    company = db.query(Company).first()
    if not company:
        print("No company found! Creating dummy company...")
        company = Company(name="Test Company", currency_code="THB")
        db.add(company)
        db.commit()

    # Sales Channel
    channel = db.query(SalesChannel).filter(SalesChannel.code == "MANUAL").first()
    if not channel:
        print("Creating MANUAL channel...")
        channel = SalesChannel(code="MANUAL", name="Manual Order")
        db.add(channel)
        db.commit()

    # Atomic Product
    sku_atom = f"TEST_ATOM_{uuid4().hex[:8]}"
    p_atom = Product(
        sku=sku_atom,
        name="Test Atomic Product",
        product_type="NORMAL",
        is_active=True
    )
    db.add(p_atom)
    db.commit()
    db.refresh(p_atom)
    print(f"Created Atomic: {p_atom.sku} (ID: {p_atom.id})")

    # Bundle Product
    sku_bundle = f"TEST_BUNDLE_{uuid4().hex[:8]}"
    p_bundle = Product(
        sku=sku_bundle,
        name="Test Bundle Product",
        product_type="SET",
        is_active=True
    )
    db.add(p_bundle)
    db.commit()
    db.refresh(p_bundle)
    print(f"Created Bundle: {p_bundle.sku} (ID: {p_bundle.id})")

    # Link Bundle -> 2 x Atom
    bom = ProductSetBom(
        set_product_id=p_bundle.id,
        component_product_id=p_atom.id,
        quantity=2
    )
    db.add(bom)
    db.commit()
    print("Linked Bundle -> 2 x Atomic")

    # Order
    order = OrderHeader(
        id=uuid4(),
        # order_number removed
        channel_code="MANUAL",
        company_id=company.id, 
        status_normalized="READY_TO_SHIP",
        order_datetime=datetime.now(),
        external_order_id=f"TEST_ORD_{uuid4().hex[:8]}"
    )
    db.add(order)
    
    # Order Item (The Bundle)
    item = OrderItem(
        id=uuid4(),
        order_id=order.id,
        sku=sku_bundle, 
        product_name="Test Bundle Item",
        quantity=1,
        unit_price=100,
        product_id=p_bundle.id
    )
    db.add(item)
    db.commit()
    print(f"Created Order: {order.external_order_id} with 1 x Bundle")

    # 2. Run Logic
    print("Running process_order_deduction...")
    StockService.process_order_deduction(db, order, wh.id)

    # 3. Check Ledger
    print("\n--- Stock Ledger Results ---")
    movements = db.query(StockLedger).filter(
        StockLedger.reference_id == str(order.id),
        StockLedger.movement_type == 'OUT'
    ).all()

    found_bundle_deduction = False
    found_atom_deduction = False

    for m in movements:
        # Get product via query slightly safer against session detaching
        p = db.query(Product).get(m.product_id)
        if not p:
            print(f"OUT: Unknown Product {m.product_id} x {m.quantity}")
            continue
            
        print(f"OUT: {p.sku} x {m.quantity}")
        if p.id == p_bundle.id:
            found_bundle_deduction = True
        if p.id == p_atom.id:
            found_atom_deduction = True

    print("\n--- Verdict ---")
    if found_bundle_deduction and not found_atom_deduction:
        print("FAIL: Deducted Bundle (Parent) - Current Behavior")
    elif found_atom_deduction and not found_bundle_deduction:
        print("PASS: Deducted Atomic (Child) - Desired Behavior")
        # Check quantity
        matching_moves = [m for m in movements if m.product_id == p_atom.id]
        total_qty = sum(m.quantity for m in matching_moves)
        if total_qty == 2:
             print("(And quantity is correct: 2)")
        else:
             print(f"(But quantity is wrong! Expected 2, Got {total_qty})")
    else:
        print(f"UNKNOWN Result (Bundle={found_bundle_deduction}, Atom={found_atom_deduction})")

if __name__ == "__main__":
    try:
        test_current_logic()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
    finally:
        db.close()
