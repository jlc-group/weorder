
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc, String
from datetime import datetime, time, timezone, timedelta
from typing import List, Dict, Any
from zoneinfo import ZoneInfo
from uuid import UUID

from app.core import settings
from app.models import OrderHeader, OrderItem


class ReportService:
    
    @staticmethod
    def get_daily_outbound_stats(db: Session, date: datetime.date, warehouse_id: str = None, cutoff_hour: int = 12) -> Dict[str, Any]:
        """
        Get statistics of items shipped on a specific date.
        Uses rts_time (Ready to Ship time) as the stable date anchor.
        Supports 'Batch Awareness' via cutoff_hour (default 12 for noon-to-noon GMT+7).
        """
        from app.models.mapping import PlatformListing
        from app.models.product import Product

        # Timezone Handling
        try:
            tz = ZoneInfo(settings.TIMEZONE)
        except:
            tz = ZoneInfo("UTC")

        # Start/End Handling with Cut-off
        # A 12:00 PM cut-off means "Jan 11 Report" covers:
        # Jan 10 12:00:00 Thai (GMT+7) -> Jan 11 11:59:59 Thai (GMT+7)
        target_day_noon = datetime.combine(date, time(cutoff_hour, 0, 0)).replace(tzinfo=tz)
        
        if cutoff_hour > 0:
            start_local = target_day_noon - timedelta(days=1)
            end_local = target_day_noon - timedelta(seconds=1)
        else:
            # Standard Midnight to Midnight
            start_local = datetime.combine(date, time.min).replace(tzinfo=tz)
            end_local = datetime.combine(date, time.max).replace(tzinfo=tz)
        
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        
        # 1. Fetch Orders + Items anchored by rts_time
        query = db.query(
            OrderHeader.id,
            OrderHeader.channel_code,
            OrderItem.sku,
            OrderItem.product_name,
            OrderItem.quantity
        ).join(OrderHeader, OrderItem.order_id == OrderHeader.id)
        
        query = query.filter(
            OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED', 'PENDING', 'UNPAID']),
            OrderHeader.rts_time >= start_utc,
            OrderHeader.rts_time <= end_utc
        )
        
        if warehouse_id:
            try:
                w_uuid = UUID(warehouse_id)
                query = query.filter(OrderHeader.warehouse_id == w_uuid)
            except ValueError:
                pass

        results = query.all()

        # 2. Load Bundle Maps for resolution
        bundle_map = {}
        listings = db.query(PlatformListing).all()
        for l in listings:
            key = (l.platform, l.platform_sku)
            components = []
            for item in l.items:
                if item.product:
                    components.append({
                        "sku": item.product.sku,
                        "name": item.product.name,
                        "qty": item.quantity
                    })
            if components:
                bundle_map[key] = components

        # 3. Aggregate Data with Bundle Resolution
        aggregated_items = {} # SKU -> {name, qty, order_count_set}
        platform_stats = {} # Platform -> {orders: set(), items: 0}
        global_orders = set()

        for order_id, platform, sku, name, qty in results:
            qty = int(qty or 0)
            if not qty: continue
            
            # Platform Stats
            if platform not in platform_stats:
                platform_stats[platform] = {"orders": set(), "items": 0}
            
            platform_stats[platform]["orders"].add(order_id)
            global_orders.add(order_id)

            # Resolve Components
            key = (platform, sku)
            resolved = []
            
            if key in bundle_map:
                for comp in bundle_map[key]:
                    resolved.append({
                        "sku": comp["sku"],
                        "name": comp["name"],
                        "qty": comp["qty"] * qty
                    })
            else:
                resolved.append({
                    "sku": sku,
                    "name": name,
                    "qty": qty
                })

            # Aggregate
            for item in resolved:
                i_sku = item["sku"]
                i_qty = item["qty"]
                i_name = item["name"]
                
                if i_sku not in aggregated_items:
                    aggregated_items[i_sku] = {
                        "name": i_name,
                        "qty": 0,
                        "orders": set()
                    }
                aggregated_items[i_sku]["qty"] += i_qty
                aggregated_items[i_sku]["orders"].add(order_id)
                platform_stats[platform]["items"] += i_qty

        # 4. Format Results
        items_data = []
        for sku, data in aggregated_items.items():
            items_data.append({
                "sku": sku,
                "product_name": data["name"],
                "total_quantity": data["qty"],
                "order_count": len(data["orders"])
            })
            
        items_data.sort(key=lambda x: x["total_quantity"], reverse=True)
        
        final_platform_stats = {}
        for p, data in platform_stats.items():
            final_platform_stats[p] = {
                "orders": len(data["orders"]),
                "items": data["items"]
            }

        return {
            "date": date.isoformat(),
            "cutoff_hour": cutoff_hour,
            "window_start": start_local.isoformat(),
            "window_end": end_local.isoformat(),
            "total_skus": len(items_data),
            "total_items": sum(i["total_quantity"] for i in items_data),
            "total_orders": len(global_orders),
            "items": items_data,
            "platforms": final_platform_stats
        }

