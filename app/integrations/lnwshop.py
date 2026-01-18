"""
LnwShop Open API Client
API Documentation: https://lnwshop.com/openapi
"""
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .base import BasePlatformClient, NormalizedOrder

logger = logging.getLogger(__name__)


class LnwShopClient(BasePlatformClient):
    """
    LnwShop Open API Client
    
    Uses X-API-KEY for authentication
    Base URL: https://open.lnwshop.com/{shop_id}/api/v1/
    """
    PLATFORM_NAME = "lnwshop"
    
    BASE_URL = "https://open.lnwshop.com"
    API_VERSION = "v1"
    
    # Status mapping
    STATUS_MAP = {
        "pending": "NEW",
        "wait_payment": "WAIT_PAY",
        "paid": "PAID",
        "wait_shipping": "READY_TO_SHIP",
        "shipping": "SHIPPED",
        "complete": "DELIVERED",
        "cancelled": "CANCELLED",
        "refund": "RETURNED",
    }
    
    def __init__(
        self,
        api_key: str,
        shop_id: str,
        shop_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LnwShop client
        
        Args:
            api_key: X-API-KEY from LnwShop
            shop_id: Shop ID (e.g., julaherbonline)
        """
        super().__init__(
            app_key=api_key,
            app_secret="",  # LnwShop uses API key only
            shop_id=shop_id,
            **kwargs
        )
        self.api_key = api_key
        self.shop_name = shop_name or shop_id
        
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with API key"""
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    def _build_url(self, endpoint: str) -> str:
        """Build full API URL"""
        return f"{self.BASE_URL}/{self.shop_id}/api/{self.API_VERSION}/{endpoint}"
    
    # ========== Authentication ==========
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """LnwShop doesn't use OAuth - API key is used directly"""
        return ""
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Not applicable for LnwShop"""
        return {}
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Not applicable for LnwShop"""
        return {}
    
    # ========== Orders ==========
    
    async def get_orders(
        self,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Get list of orders from LnwShop
        API: POST /{shop_id}/api/v1/order/list
        """
        url = self._build_url("order/list")
        headers = self._build_headers()
        
        payload = {
            "pagination_limit": min(page_size, 100),
            "pagination_offset": int(cursor) if cursor else 0,
        }
        
        if time_from:
            payload["order_create_time_from"] = time_from.strftime("%Y-%m-%d %H:%M:%S")
        if time_to:
            payload["order_create_time_to"] = time_to.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                self._log_api_call("POST", "order/list", response.status_code)
                
                if response.status_code != 200:
                    logger.error(f"LnwShop API error: {response.text}")
                    return {"orders": [], "total": 0, "has_more": False}
                
                data = response.json()
                
                if data.get("error"):
                    raise Exception(f"LnwShop API Error: {data.get('error_message')}")
                
                orders = data.get("data", {}).get("orders", [])
                total = data.get("data", {}).get("total", 0)
                current_offset = int(cursor) if cursor else 0
                
                return {
                    "orders": orders,
                    "next_cursor": str(current_offset + len(orders)) if len(orders) == page_size else None,
                    "total": total,
                    "has_more": current_offset + len(orders) < total,
                }
                
        except httpx.RequestError as e:
            logger.error(f"LnwShop request error: {e}")
            return {"orders": [], "total": 0, "has_more": False}
    
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed order information
        API: POST /{shop_id}/api/v1/order/info
        """
        url = self._build_url("order/info")
        headers = self._build_headers()
        
        payload = {"order_id": order_id}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                self._log_api_call("POST", "order/info", response.status_code)
                
                if response.status_code != 200:
                    return {}
                
                data = response.json()
                return data.get("data", {}).get("order", {})
                
        except Exception as e:
            logger.error(f"Error fetching order detail {order_id}: {e}")
            return {}
    
    async def update_tracking(
        self, 
        order_id: str, 
        tracking_number: str, 
        shipping_provider: str
    ) -> bool:
        """
        Update order with tracking information
        API: POST /{shop_id}/api/v1/order/set_deliver
        """
        url = self._build_url("order/set_deliver")
        headers = self._build_headers()
        
        payload = {
            "order_id": order_id,
            "shipping_provider": shipping_provider,
            "track_code": tracking_number,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                self._log_api_call("POST", "order/set_deliver", response.status_code)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("success", False)
                return False
                
        except Exception as e:
            logger.error(f"Error updating tracking for {order_id}: {e}")
            return False
    
    def normalize_order(self, raw_order: Dict[str, Any]) -> NormalizedOrder:
        """Convert LnwShop order to normalized format"""
        
        # Parse customer info
        customer = raw_order.get("customer", {})
        shipping = raw_order.get("shipping", {})
        
        # Parse items
        items = []
        for item in raw_order.get("items", []):
            items.append({
                "platform_item_id": str(item.get("product_id", "")),
                "sku": item.get("sku", ""),
                "product_name": item.get("name", ""),
                "quantity": int(item.get("quantity", 1)),
                "unit_price": float(item.get("price", 0)),
                "total_price": float(item.get("price", 0)) * int(item.get("quantity", 1)),
                "variation": item.get("option", ""),
                "image_url": item.get("image", ""),
            })
        
        # Parse dates
        order_date = None
        if raw_order.get("create_time"):
            try:
                order_date = datetime.fromisoformat(raw_order["create_time"].replace("Z", "+00:00"))
            except:
                pass
        
        paid_at = None
        if raw_order.get("payment_time"):
            try:
                paid_at = datetime.fromisoformat(raw_order["payment_time"].replace("Z", "+00:00"))
            except:
                pass
        
        shipped_at = None
        if raw_order.get("shipping_time"):
            try:
                shipped_at = datetime.fromisoformat(raw_order["shipping_time"].replace("Z", "+00:00"))
            except:
                pass
        
        return NormalizedOrder(
            platform_order_id=str(raw_order.get("order_id", "")),
            platform="lnwshop",
            
            customer_name=customer.get("name", ""),
            customer_phone=customer.get("phone", ""),
            customer_email=customer.get("email", ""),
            
            shipping_name=shipping.get("name", "") or customer.get("name", ""),
            shipping_phone=shipping.get("phone", "") or customer.get("phone", ""),
            shipping_address=shipping.get("address", ""),
            shipping_district=shipping.get("district", ""),
            shipping_city=shipping.get("city", ""),
            shipping_province=shipping.get("province", ""),
            shipping_postal_code=shipping.get("postcode", ""),
            shipping_country="TH",
            
            order_status=raw_order.get("status", ""),
            status_normalized=self.normalize_order_status(raw_order.get("status", "")),
            
            subtotal=float(raw_order.get("subtotal", 0)),
            shipping_fee=float(raw_order.get("shipping_fee", 0)),
            discount=float(raw_order.get("discount", 0)),
            total_amount=float(raw_order.get("total", 0)),
            
            payment_method=raw_order.get("payment_method", ""),
            paid_at=paid_at,
            
            shipping_method=raw_order.get("shipping_method", ""),
            tracking_number=raw_order.get("tracking_code", ""),
            courier=raw_order.get("shipping_provider", ""),
            
            order_created_at=order_date,
            order_updated_at=None,
            shipped_at=shipped_at,
            
            items=items,
            raw_payload=raw_order,
        )
    
    def normalize_order_status(self, platform_status: str) -> str:
        """Map LnwShop status to normalized status"""
        return self.STATUS_MAP.get(platform_status.lower(), "NEW")
    
    # ========== Webhooks ==========
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """LnwShop webhook verification (if supported)"""
        # TODO: Implement if LnwShop provides webhook signature
        return True
    
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LnwShop webhook payload"""
        return {
            "event_type": payload.get("event"),
            "order_id": payload.get("order_id"),
            "shop_id": self.shop_id,
            "timestamp": payload.get("timestamp"),
            "data": payload,
        }
