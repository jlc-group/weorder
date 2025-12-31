"""
TikTok Shop Open API Client - V2
API Documentation: https://partner.tiktokshop.com/docv2
"""
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
import logging

from .base import BasePlatformClient, NormalizedOrder

logger = logging.getLogger(__name__)


class TikTokClient(BasePlatformClient):
    """
    TikTok Shop Open API Client - V2
    """
    PLATFORM_NAME = "tiktok"
    
    # API Endpoints - V2
    BASE_URL = "https://open-api.tiktokglobalshop.com"
    AUTH_URL = "https://auth.tiktok-shops.com/oauth/authorize"
    API_VERSION = "202309"  # V2 API version
    
    # Status mapping
    STATUS_MAP = {
        "UNPAID": "WAIT_PAY",
        "AWAITING_SHIPMENT": "PAID",
        "AWAITING_COLLECTION": "PACKING",
        "IN_TRANSIT": "SHIPPED",
        "DELIVERED": "DELIVERED",
        "COMPLETED": "DELIVERED",
        "CANCELLED": "CANCELLED",
        "CANCELLATION_REQUESTED": "CANCELLED",
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
        self.shop_cipher = ""  # TikTok uses shop_cipher for multi-shop in V2
    
    # ========== Signature V2 ==========
    
    def _generate_signature_v2(self, path: str, params: Dict[str, str], body: Optional[Dict] = None) -> str:
        """
        Generate TikTok API V2 signature
        Sign = HMAC-SHA256(secret, secret + path + params_string + body_string + secret)
        params_string = sorted query parameters concatenated as key+value (exclude sign, access_token)
        """
        # Exclude 'sign' and 'access_token' from signature params
        sign_params = {k: str(v) for k, v in params.items() if k not in ['sign', 'access_token']}
        
        # Sort parameters alphabetically and concatenate
        sorted_params = sorted(sign_params.items())
        params_string = "".join(f"{k}{v}" for k, v in sorted_params)
        
        # Body string (if POST with JSON body)
        body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body else ""
        
        # Build sign string: secret + path + params + body + secret
        sign_string = f"{self.app_secret}{path}{params_string}{body_str}{self.app_secret}"
        
        # HMAC-SHA256
        signature = hmac.new(
            self.app_secret.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _make_request(
        self,
        api_path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated API request - V2"""
        await self.ensure_valid_token()
        
        timestamp = int(time.time())
        
        # Build V2 API path - format: /order/202309/orders/search
        full_path = f"/order/{self.API_VERSION}/orders{api_path}"
        
        # V2 request params
        request_params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.shop_id,
        }
        
        # Generate signature BEFORE adding access_token
        signature = self._generate_signature_v2(full_path, request_params, body)
        request_params["sign"] = signature
        
        # Now add access_token (not included in signature)
        if self.access_token:
            request_params["access_token"] = self.access_token
        
        url = f"{self.BASE_URL}{full_path}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "x-tts-access-token": self.access_token or "",
            }
            
            if method == "GET":
                response = await client.get(url, params=request_params, headers=headers)
            else:
                response = await client.post(url, params=request_params, json=body, headers=headers)
            
            self._log_api_call(method, full_path, response.status_code)
            data = response.json()
            
            # V2 success check
            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"TikTok API V2 Error: {error_msg} - Response: {data}")
                raise Exception(f"TikTok API Error: {error_msg}")
            
            return data.get("data", {})
    
    # ========== Authentication ==========
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Generate OAuth authorization URL"""
        params = {
            "app_key": self.app_key,
            "state": "weorder",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        path = "/api/v2/token/get"
        
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "auth_code": code,
            "grant_type": "authorized_code",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{path}",
                params=params,
            )
            
            self._log_api_call("GET", path, response.status_code)
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"TikTok API Error: {data.get('message')}")
            
            token_data = data.get("data", {})
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("access_token_expire_in", 86400),
            }
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        path = "/api/v2/token/refresh"
        
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{path}",
                params=params,
            )
            
            self._log_api_call("GET", path, response.status_code)
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"TikTok API Error: {data.get('message')}")
            
            token_data = data.get("data", {})
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("access_token_expire_in", 86400),
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
        Get list of orders from TikTok Shop - V2 API
        API: /orders/search
        """
        body = {
            "page_size": min(page_size, 100),
        }
        
        if time_from:
            body["create_time_ge"] = int(time_from.timestamp())
        if time_to:
            body["create_time_lt"] = int(time_to.timestamp())
        if status:
            body["order_status"] = status  # V2 uses string, not array
        if cursor:
            body["cursor"] = cursor
        
        try:
            data = await self._make_request("/search", method="POST", body=body)
            orders = data.get("orders", [])
            
            return {
                "orders": orders,
                "next_cursor": data.get("next_cursor"),
                "total": data.get("total_count", len(orders)),
                "has_more": bool(data.get("next_cursor")),
            }
        except Exception as e:
            logger.error(f"Error fetching TikTok orders: {e}")
            # Return empty result on error instead of crashing
            return {
                "orders": [],
                "next_cursor": None,
                "total": 0,
                "has_more": False,
            }
    
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed order information - V2 API
        API: /orders/detail/query
        """
        try:
            body = {"order_id_list": [order_id]}
            data = await self._make_request("/detail/query", method="POST", body=body)
            orders = data.get("orders", [])
            return orders[0] if orders else {}
        except Exception as e:
            logger.error(f"Error fetching TikTok order detail {order_id}: {e}")
            return {}
    
    def normalize_order(self, raw_order: Dict[str, Any]) -> NormalizedOrder:
        """Convert TikTok order to normalized format"""
        recipient = raw_order.get("recipient_address", {})
        
        # Parse items
        items = []
        for item in raw_order.get("line_items", []):
            items.append({
                "platform_item_id": str(item.get("id")),
                "sku": item.get("seller_sku", ""),
                "product_name": item.get("product_name", ""),
                "quantity": item.get("quantity", 1),
                "unit_price": float(item.get("sale_price", 0)) / 100,  # TikTok uses cents
                "total_price": float(item.get("sale_price", 0)) * item.get("quantity", 1) / 100,
                "variation": item.get("sku_name"),
                "image_url": item.get("sku_image"),
            })
        
        # Calculate totals (TikTok amounts are in cents)
        payment = raw_order.get("payment", {})
        total_amount = float(payment.get("total_amount", 0)) / 100
        shipping_fee = float(payment.get("shipping_fee", 0)) / 100
        
        return NormalizedOrder(
            platform_order_id=raw_order.get("id", ""),
            platform="tiktok",
            
            customer_name=recipient.get("name", ""),
            customer_phone=recipient.get("phone_number", ""),
            
            shipping_name=recipient.get("name", ""),
            shipping_phone=recipient.get("phone_number", ""),
            shipping_address=recipient.get("full_address", ""),
            shipping_district=recipient.get("district_info", [{}])[0].get("district_name", "") if recipient.get("district_info") else "",
            shipping_city=recipient.get("city", ""),
            shipping_province=recipient.get("state", ""),
            shipping_postal_code=recipient.get("postal_code", ""),
            shipping_country=recipient.get("region_code", "TH"),
            
            order_status=raw_order.get("status", ""),
            status_normalized=self.normalize_order_status(raw_order.get("status", "")),
            
            subtotal=total_amount - shipping_fee,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            
            payment_method=payment.get("payment_method_name", ""),
            
            tracking_number=raw_order.get("packages", [{}])[0].get("tracking_number") if raw_order.get("packages") else None,
            courier=raw_order.get("packages", [{}])[0].get("shipping_provider_name") if raw_order.get("packages") else None,
            
            order_created_at=datetime.fromtimestamp(raw_order["create_time"]) if raw_order.get("create_time") else None,
            order_updated_at=datetime.fromtimestamp(raw_order["update_time"]) if raw_order.get("update_time") else None,
            
            items=items,
            raw_payload=raw_order,
        )
    
    def normalize_order_status(self, platform_status: str) -> str:
        """Map TikTok status to normalized status"""
        return self.STATUS_MAP.get(platform_status, "NEW")
    
    # ========== Webhooks ==========
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify TikTok webhook signature
        sign = HMAC-SHA256(app_secret, app_secret + timestamp + body + app_secret)
        """
        sign_string = f"{self.app_secret}{timestamp or ''}{payload.decode()}{self.app_secret}"
        
        expected = hmac.new(
            self.app_secret.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse TikTok webhook payload"""
        return {
            "event_type": payload.get("type"),  # ORDER_STATUS_CHANGE, ORDER_CREATE
            "order_id": payload.get("data", {}).get("order_id"),
            "shop_id": payload.get("shop_id"),
            "timestamp": payload.get("timestamp"),
            "data": payload.get("data", {}),
        }
