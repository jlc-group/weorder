
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc, String
from datetime import datetime, time, timezone, timedelta
from typing import List, Dict, Any
from zoneinfo import ZoneInfo
from uuid import UUID

from app.core import settings
from app.models import OrderHeader, OrderItem
from app.models.label_log import LabelPrintLog


class ReportService:
    
    @staticmethod
    def get_daily_outbound_stats(db: Session, date: datetime.date, warehouse_id: str = None, cutoff_hour: int = 0, date_mode: str = "collection") -> Dict[str, Any]:
        """
        Get statistics of items shipped on a specific date.
        
        Args:
            date_mode: 
                - "collection" (default): Uses collection_time (courier pickup)
                - "rts": Uses rts_time (ready to ship / packing date)
        """
        from app.models.mapping import PlatformListing
        from app.models.product import Product
        from sqlalchemy import or_

        # Timezone Handling
        try:
            tz = ZoneInfo(settings.TIMEZONE)
        except:
            tz = ZoneInfo("Asia/Bangkok")

        # Query using date range
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        
        # 1. Fetch Orders + Items
        query = db.query(
            OrderHeader.id,
            OrderHeader.channel_code,
            OrderItem.sku,
            OrderItem.product_name,
            OrderItem.quantity
        ).join(OrderHeader, OrderItem.order_id == OrderHeader.id)
        
        # Apply date filter based on mode
        if date_mode == "rts":
            # RTS mode: use rts_time (packing/label print date)
            query = query.filter(
                OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED']),
                or_(
                    # Primary: rts_time
                    (OrderHeader.rts_time >= start_dt) & (OrderHeader.rts_time <= end_dt),
                    # Fallback: collection_time when rts_time is null
                    (OrderHeader.rts_time.is_(None)) & (OrderHeader.collection_time >= start_dt) & (OrderHeader.collection_time <= end_dt)
                )
            )
        else:
            # Default: collection mode (courier pickup)
            query = query.filter(
                OrderHeader.status_normalized.notin_(['CANCELLED', 'RETURNED']),
                or_(
                    # Primary: courier collection_time
                    (OrderHeader.collection_time >= start_dt) & (OrderHeader.collection_time <= end_dt),
                    # Fallback: shipped_at when collection_time is null
                    (OrderHeader.collection_time.is_(None)) & (OrderHeader.shipped_at >= start_dt) & (OrderHeader.shipped_at <= end_dt)
                )
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
            "window_start": start_dt.isoformat(),
            "window_end": end_dt.isoformat(),
            "total_skus": len(items_data),
            "total_items": sum(i["total_quantity"] for i in items_data),
            "total_orders": len(global_orders),
            "items": items_data,
            "platforms": final_platform_stats,
            # Add label stats for accurate "packed" counts
            "label_stats": ReportService.get_label_stats(db, date),
            # Data quality note
            "data_note": "TikTok uses courier collection_time. Shopee uses pickup_done_time. Lazada falls back to shipped_at.",
        }

    @staticmethod
    def get_label_stats(db: Session, target_date: datetime.date) -> Dict[str, Any]:
        """
        Get label print stats for a specific date.
        This is the accurate "packed/shipped" count based on when labels were printed.
        """
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        
        # Query label logs for the date
        results = db.query(
            LabelPrintLog.platform,
            func.count(LabelPrintLog.id).label('count')
        ).filter(
            LabelPrintLog.printed_at >= start_dt,
            LabelPrintLog.printed_at <= end_dt
        ).group_by(LabelPrintLog.platform).all()
        
        platforms = {}
        total = 0
        for platform, count in results:
            platforms[platform or 'unknown'] = count
            total += count
        
        return {
            "total_labels": total,
            "by_platform": platforms,
            "source": "label_print_log"
        }
