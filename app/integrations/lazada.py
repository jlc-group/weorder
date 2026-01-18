"""
Lazada Open Platform Client
API Documentation: https://open.lazada.com/apps/doc/api
"""
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
import logging

from .base import BasePlatformClient, NormalizedOrder

logger = logging.getLogger(__name__)


class LazadaClient(BasePlatformClient):
    """
    Lazada Open Platform API Client
    """
    PLATFORM_NAME = "lazada"
    
    # API Endpoints (Thailand)
    BASE_URL = "https://api.lazada.co.th/rest"
    AUTH_URL = "https://auth.lazada.com/oauth/authorize"
    TOKEN_URL = "https://auth.lazada.com/rest/auth/token/create"
    REFRESH_URL = "https://auth.lazada.com/rest/auth/token/refresh"
    
    # Status mapping
    STATUS_MAP = {
        "unpaid": "WAIT_PAY",
        "pending": "NEW",
        "ready_to_ship": "READY_TO_SHIP",
        "ready_to_ship_pending": "READY_TO_SHIP",
        "shipped": "SHIPPED",
        "delivered": "DELIVERED",
        "failed": "CANCELLED",
        "canceled": "CANCELLED",
        "returned": "RETURNED",
    }
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        shop_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        super().__init__(app_key, app_secret, shop_id, access_token, refresh_token)
    
    # ========== Signature ==========
    
    def _generate_signature(self, api_path: str, params: Dict[str, Any]) -> str:
        """
        Generate Lazada API signature
        sign = HMAC-SHA256(sorted_params, app_secret)
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())
        
        # Concatenate api path and parameters
        sign_string = api_path
        for key, value in sorted_params:
            sign_string += f"{key}{value}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_secret.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest().upper()
        
        return signature
    
    async def _make_request(
        self,
        api_path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated API request"""
        await self.ensure_valid_token()
        
        request_params = params or {}
        request_params.update({
            "app_key": self.app_key,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
        })
        
        if self.access_token:
            request_params["access_token"] = self.access_token
        
        # Generate signature
        request_params["sign"] = self._generate_signature(api_path, request_params)
        
        url = f"{self.BASE_URL}{api_path}"
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=request_params)
            else:
                response = await client.post(url, params=request_params, json=body)
            
            self._log_api_call(method, api_path, response.status_code)
            data = response.json()
            
            if data.get("code") != "0":
                raise Exception(f"Lazada API Error: {data.get('message')}")
            
            return data.get("data", {})
    
    # ========== Authentication ==========
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Generate OAuth authorization URL"""
        params = {
            "response_type": "code",
            "force_auth": "true",
            "redirect_uri": redirect_uri,
            "client_id": self.app_key,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        timestamp = str(int(time.time() * 1000))
        
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
            "code": code,
        }
        params["sign"] = self._generate_signature("/auth/token/create", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, params=params)
            self._log_api_call("POST", "/auth/token/create", response.status_code)
            data = response.json()
            
            if data.get("code") != "0":
                raise Exception(f"Lazada API Error: {data.get('message')}")
            
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 604800),  # 7 days
            }
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        timestamp = str(int(time.time() * 1000))
        
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
            "refresh_token": self.refresh_token,
        }
        params["sign"] = self._generate_signature("/auth/token/refresh", params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.REFRESH_URL, params=params)
            self._log_api_call("POST", "/auth/token/refresh", response.status_code)
            data = response.json()
            
            if data.get("code") != "0":
                raise Exception(f"Lazada API Error: {data.get('message')}")
            
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 604800),
            }
    
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
        Get list of orders from Lazada
        API: /orders/get
        """
        params = {
            "limit": str(min(page_size, 100)),
            "sort_by": "created_at",
            "sort_direction": "DESC",
        }
        
        if time_from:
            params["created_after"] = time_from.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        if time_to:
            params["created_before"] = time_to.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        if status:
            params["status"] = status
        if cursor:
            params["offset"] = cursor
        
        data = await self._make_request("/orders/get", params=params)
        orders = data.get("orders", [])
        
        return {
            "orders": orders,
            "next_cursor": str(int(cursor or 0) + len(orders)) if orders else None,
            "total": data.get("countTotal", len(orders)),
            "has_more": len(orders) == page_size,
        }
    
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed order information
        API: /order/get + /order/items/get
        """
        data = await self._make_request("/order/get", params={"order_id": order_id})
        
        # Also fetch items and attach them to the order data
        try:
            items = await self.get_order_items(order_id)
            if items:
                data["order_items"] = items
        except Exception as e:
            logger.error(f"Error fetching items for Lazada order {order_id}: {e}")
            
        return data
    
    async def get_order_items(self, order_id: str) -> list:
        """
        Get order items
        API: /order/items/get
        """
        data = await self._make_request("/order/items/get", params={"order_id": order_id})
        if isinstance(data, list):
            return data
        return data.get("items", [])

    # ========== Finance ==========

    async def get_transaction_details(
        self,
        time_from: datetime,
        time_to: datetime,
        trans_type: Optional[str] = None
    ) -> list:
        """
        Get transaction details
        API: /finance/transaction/detail/get
        """
        params = {
            "start_time": time_from.strftime("%Y-%m-%d"),
            "end_time": time_to.strftime("%Y-%m-%d"),
        }
        if trans_type:
            params["trans_type"] = trans_type
            
        # Lazada Finance API often returns a list directly or inside a key
        data = await self._make_request("/finance/transaction/detail/get", params=params)
        return data if isinstance(data, list) else data.get("data", [])

    def normalize_order(self, raw_order: Dict[str, Any]) -> NormalizedOrder:
        """Convert Lazada order to normalized format"""
        address = raw_order.get("address_shipping", {})
        
        # Parse items (need separate API call)
        items = []
        for item in raw_order.get("order_items", []):
            items.append({
                "platform_item_id": str(item.get("order_item_id")),
                "sku": item.get("sku", ""),
                "product_name": item.get("name", ""),
                "quantity": 1,  # Lazada reports items individually
                "unit_price": float(item.get("paid_price", 0)),
                "total_price": float(item.get("paid_price", 0)),
                "variation": item.get("variation"),
            })
        
        status_raw = raw_order.get("statuses", [""])[0] if raw_order.get("statuses") else ""
        status_norm = self.normalize_order_status(status_raw)
        updated_at = datetime.fromisoformat(raw_order["updated_at"].replace("Z", "+00:00")) if raw_order.get("updated_at") else None
        
        # Fallback for shipped_at since Lazada doesn't provide it
        shipped_at = None
        if status_norm in ["SHIPPED", "DELIVERED", "COMPLETED"]:
            shipped_at = updated_at

        return NormalizedOrder(
            platform_order_id=str(raw_order.get("order_id", "")),
            platform="lazada",
            
            customer_name=raw_order.get("customer_first_name", "") + " " + raw_order.get("customer_last_name", ""),
            customer_phone=address.get("phone"),
            
            shipping_name=address.get("first_name", "") + " " + address.get("last_name", ""),
            shipping_phone=address.get("phone", ""),
            shipping_address=address.get("address1", "") + " " + address.get("address2", ""),
            shipping_city=address.get("city", ""),
            shipping_province=address.get("address3", ""),
            shipping_postal_code=address.get("post_code", ""),
            shipping_country=address.get("country", "TH"),
            
            order_status=status_raw,
            status_normalized=status_norm,
            
            subtotal=float(raw_order.get("price", 0)),
            shipping_fee=float(raw_order.get("shipping_fee", 0)),
            total_amount=float(raw_order.get("price", 0)),
            
            payment_method=raw_order.get("payment_method", ""),
            
            order_created_at=datetime.fromisoformat(raw_order["created_at"].replace("Z", "+00:00")) if raw_order.get("created_at") else None,
            order_updated_at=updated_at,
            shipped_at=shipped_at,
            
            items=items,
            raw_payload=raw_order,

        )
    
    def normalize_order_status(self, platform_status: str) -> str:
        """Map Lazada status to normalized status"""
        return self.STATUS_MAP.get(platform_status.lower(), "NEW")
    
    # ========== Webhooks ==========
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Verify Lazada webhook signature"""
        expected = hmac.new(
            self.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Lazada webhook payload"""
        return {
            "event_type": payload.get("message_type"),  # ORDER_CREATED, ORDER_STATUS_CHANGED
            "order_id": str(payload.get("data", {}).get("trade_order_id")),
            "timestamp": payload.get("timestamp"),
            "data": payload.get("data", {}),
        }

    async def get_order_trace(self, order_id: str) -> Optional[Dict]:
        """
        Get order tracking trace/history
        API: /logistic/order/trace (GetOrderTrace)
        
        Returns tracking events including "Picked Up" or "Scanned" events with event_time
        """
        try:
            data = await self._make_request("/logistic/order/trace", params={"order_id": order_id})
            return data
        except Exception as e:
            logger.error(f"Error fetching order trace for {order_id}: {e}")
            return None

    def extract_pickup_time_from_trace(self, trace_data: Dict) -> Optional[datetime]:
        """
        Extract pickup time from order trace by finding "Picked Up" or "Scanned" event
        
        Returns datetime when package was picked up by courier
        """
        if not trace_data:
            return None
            
        # Lazada trace data structure - may be in 'module' or directly in data
        events = trace_data.get("module", [])
        if not events and isinstance(trace_data, list):
            events = trace_data
            
        pickup_keywords = [
            "picked up",
            "successful turn over",
            "scanned",
            "collected",
            "received from seller",
            "รับพัสดุ",
            "รับสินค้า"
        ]
        
        for event in events:
            title = (event.get("title") or event.get("code") or "").lower()
            description = (event.get("description") or "").lower()
            
            if any(keyword in title or keyword in description for keyword in pickup_keywords):
                event_time = event.get("event_time") or event.get("time")
                if event_time:
                    try:
                        # Handle different time formats
                        if isinstance(event_time, str):
                            # Format: YYYY-MM-DD HH:mm:ss or ISO format
                            if "T" in event_time:
                                return datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                            else:
                                return datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S")
                        elif isinstance(event_time, (int, float)):
                            return datetime.fromtimestamp(event_time)
                    except Exception as e:
                        logger.warning(f"Failed to parse event_time {event_time}: {e}")
        
        return None

