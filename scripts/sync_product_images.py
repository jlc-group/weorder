import sys
import os
import json
from sqlalchemy import or_
sys.path.append(os.getcwd())

from app.core import SessionLocal
from app.models.order import OrderHeader
from app.models.product import Product

def sync_product_images():
    db = SessionLocal()
    try:
        # Get all products that don't have an image
        products_without_image = db.query(Product).filter(
            or_(Product.image_url == None, Product.image_url == "")
        ).all()
        
        target_skus = {p.sku: p for p in products_without_image}
        print(f"Checking {len(target_skus)} products without images...")
        
        if not target_skus:
            print("No products need images.")
            return

        # Get orders with payloads (focused on TikTok as known source of images)
        orders = db.query(OrderHeader).filter(
            OrderHeader.channel_code == 'tiktok',
            OrderHeader.raw_payload.isnot(None)
        ).yield_per(100)
        
        updated_count = 0
        
        for order in orders:
            if not target_skus:
                break
                
            try:
                payload = order.raw_payload
                if isinstance(payload, str):
                    payload = json.loads(payload)
                    
                if 'line_items' in payload:
                    for item in payload['line_items']:
                        sku = item.get('seller_sku')
                        image_url = item.get('sku_image')
                        
                        if sku in target_skus and image_url:
                            product = target_skus[sku]
                            print(f"Updating image for {sku}")
                            product.image_url = image_url
                            
                            # Remove from target list so we don't update again
                            del target_skus[sku]
                            updated_count += 1
                            
                            # Commit per batch or periodically could be better, but simple is fine for now
            except Exception as e:
                continue
        
        db.commit()
        print(f"\n✅ Successfully updated images for {updated_count} products.")
        
    finally:
        db.close()

if __name__ == "__main__":
    sync_product_images()
