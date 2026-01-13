"""
Pick List Service - Generate aggregated product summary for packing
"""
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from app.services import OrderService
from app.models import OrderHeader, Product

class PickListService:
    @staticmethod
    def generate_summary(db: Session, order_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Aggregate items from given orders.
        Explode SET products into components.
        Return list of items sorted by SKU.
        """
        # 1. Fetch orders
        # Convert IDs
        valid_uuids = []
        external_ids = []
        for oid in order_ids:
            try:
                valid_uuids.append(UUID(oid))
            except ValueError:
                external_ids.append(oid)
        
        # We fetch orders one by one or in batch.
        # OrderService has get_orders but maybe easier to query OrderHeader directly to join items
        
        # Let's iterate and build aggregate map
        # Map: SKU -> {name, quantity, image_url}
        summary_map = {}
        
        # Helper to add to map
        def add_item(sku, name, qty, img, components=None):
            if sku not in summary_map:
                summary_map[sku] = {
                    "sku": sku,
                    "name": name,
                    "quantity": 0,
                    "image_url": img,
                    "components": components or []
                }
            summary_map[sku]["quantity"] += qty

        from app.models import OrderItem, ProductSetBom

        # Query items directly for these orders
        query = db.query(OrderItem).join(OrderHeader).filter(
            (OrderHeader.id.in_(valid_uuids)) | (OrderHeader.external_order_id.in_(external_ids))
        ).options(
            joinedload(OrderItem.product).joinedload(Product.set_components).joinedload(ProductSetBom.component_product)
        )
        
        items = query.all()
        
        for item in items:
            product = item.product
            quantity = item.quantity
            
            if not product:
                # Fallback if product not linked
                add_item(item.sku, item.product_name, quantity, None)
                continue
                
            if product.product_type == "SET":
                # Don't explode, just list components for reference
                comps = []
                if product.set_components:
                    for bom in product.set_components:
                        comp_prod = bom.component_product
                        comps.append({
                            "sku": comp_prod.sku,
                            "name": comp_prod.name,
                            "qty": bom.quantity
                        })
                add_item(product.sku, product.name, quantity, product.image_url, components=comps)
            else:
                # Normal item
                add_item(product.sku, product.name, quantity, product.image_url)
                
        # Convert to list and sort
        result = list(summary_map.values())
        result.sort(key=lambda x: x["sku"])
        
        return result
