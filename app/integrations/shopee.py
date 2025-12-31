"""
Shopee Open Platform Client
API Documentation: https://open.shopee.com/documents
"""
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
import logging

from .base import BasePlatformClient, NormalizedOrder, NormalizedOrderItem

logger = logging.getLogger(__name__)


class ShopeeClient(BasePlatformClient):
    """
    Shopee Open Platform API Client
    """
    PLATFORM_NAME = "shopee"
    
    # API Endpoints
    BASE_URL = "https://partner.shopeemobile.com"
    AUTH_URL = "https://partner.shopeemobile.com/api/v2/shop/auth_partner"
    
    # API Version
    API_VERSION = "v2"
    
    # Status mapping
    STATUS_MAP = {
        "UNPAID": "WAIT_PAY",
        "READY_TO_SHIP": "PAID",
        "PROCESSED": "PACKING",
        "SHIPPED": "SHIPPED",
        "COMPLETED": "DELIVERED",
        "IN_CANCEL": "CANCELLED",
        "CANCELLED": "CANCELLED",
        "TO_RETURN": "RETURNED",
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
        self.partner_id = int(app_key) if app_key.isdigit() else 0
    
    # ========== Signature ==========
    
    def _generate_signature(self, path: str, timestamp: int) -> str:
        """
        Generate Shopee API signature
        signature = SHA256(partner_id + path + timestamp + access_token + shop_id + partner_key)
        """
        base_string = f"{self.partner_id}{path}{timestamp}"
        if self.access_token:
            base_string += f"{self.access_token}{self.shop_id}"
        base_string += self.app_secret
        
        return hmac.new(
            self.app_secret.encode(),
            base_string.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _build_common_params(self, path: str) -> Dict[str, Any]:
        """Build common request parameters"""
        timestamp = int(time.time())
        sign = self._generate_signature(path, timestamp)
        
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign,
        }
        
        if self.access_token:
            params["access_token"] = self.access_token
            params["shop_id"] = int(self.shop_id)
        
        return params
    
    # ========== Authentication ==========
    
    async def get_auth_url(self, redirect_uri: str) -> str:
        """Generate OAuth authorization URL"""
        timestamp = int(time.time())
        path = "/api/v2/shop/auth_partner"
        sign = self._generate_signature(path, timestamp)
        
        return (
            f"{self.BASE_URL}{path}"
            f"?partner_id={self.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
            f"&redirect={redirect_uri}"
        )
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        path = "/api/v2/auth/token/get"
        timestamp = int(time.time())
        sign = self._generate_signature(path, timestamp)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}{path}",
                params={
                    "partner_id": self.partner_id,
                    "timestamp": timestamp,
                    "sign": sign,
                },
                json={
                    "code": code,
                    "shop_id": int(self.shop_id),
                    "partner_id": self.partner_id,
                }
            )
            
            self._log_api_call("POST", path, response.status_code)
            data = response.json()
            
            if data.get("error"):
                raise Exception(f"Shopee API Error: {data.get('message')}")
            
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expire_in", 3600),
            }
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        path = "/api/v2/auth/access_token/get"
        timestamp = int(time.time())
        sign = self._generate_signature(path, timestamp)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}{path}",
                params={
                    "partner_id": self.partner_id,
                    "timestamp": timestamp,
                    "sign": sign,
                },
                json={
                    "refresh_token": self.refresh_token,
                    "shop_id": int(self.shop_id),
                    "partner_id": self.partner_id,
                }
            )
            
            self._log_api_call("POST", path, response.status_code)
            data = response.json()
            
            if data.get("error"):
                raise Exception(f"Shopee API Error: {data.get('message')}")
            
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expire_in", 3600),
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
        Get list of orders from Shopee
        API: /api/v2/order/get_order_list
        """
        await self.ensure_valid_token()
        
        path = "/api/v2/order/get_order_list"
        params = self._build_common_params(path)
        
        # Time range (default: last 7 days)
        if not time_from:
            time_from = datetime.utcnow() - timedelta(days=7)
        if not time_to:
            time_to = datetime.utcnow()
        
        params.update({
            "time_range_field": "create_time",
            "time_from": int(time_from.timestamp()),
            "time_to": int(time_to.timestamp()),
            "page_size": min(page_size, 100),
            "response_optional_fields": "order_status",
        })
        
        if status:
            params["order_status"] = status
        if cursor:
            params["cursor"] = cursor
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}{path}", params=params)
            self._log_api_call("GET", path, response.status_code)
            data = response.json()
            
            if data.get("error"):
                raise Exception(f"Shopee API Error: {data.get('message')}")
            
            resp = data.get("response", {})
            order_list = resp.get("order_list", [])
            
            return {
                "orders": order_list,
                "next_cursor": resp.get("next_cursor"),
                "total": len(order_list),
                "has_more": resp.get("more", False),
            }
    
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed order information
        API: /api/v2/order/get_order_detail
        """
        await self.ensure_valid_token()
        
        path = "/api/v2/order/get_order_detail"
        params = self._build_common_params(path)
        params["order_sn_list"] = order_id
        params["response_optional_fields"] = (
            "buyer_user_id,buyer_username,estimated_shipping_fee,"
            "recipient_address,actual_shipping_fee,goods_to_declare,"
            "note,note_update_time,item_list,pay_time,dropshipper,"
            "dropshipper_phone,split_up,buyer_cancel_reason,cancel_by,"
            "cancel_reason,actual_shipping_fee_confirmed,buyer_cpf_id,"
            "fulfillment_flag,pickup_done_time,package_list,shipping_carrier,"
            "payment_method,total_amount,buyer_username,invoice_data,"
            "checkout_shipping_carrier,reverse_shipping_fee,order_chargeable_weight_gram"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}{path}", params=params)
            self._log_api_call("GET", path, response.status_code)
            data = response.json()
            
            if data.get("error"):
                raise Exception(f"Shopee API Error: {data.get('message')}")
            
            orders = data.get("response", {}).get("order_list", [])
            return orders[0] if orders else {}
    
    def normalize_order(self, raw_order: Dict[str, Any]) -> NormalizedOrder:
        """Convert Shopee order to normalized format"""
        recipient = raw_order.get("recipient_address", {})
        
        # Parse items
        items = []
        for item in raw_order.get("item_list", []):
            items.append({
                "platform_item_id": str(item.get("item_id")),
                "sku": item.get("model_sku") or item.get("item_sku", ""),
                "product_name": item.get("item_name", ""),
                "quantity": item.get("model_quantity_purchased", 1),
                "unit_price": float(item.get("model_discounted_price", 0)),
                "total_price": float(item.get("model_discounted_price", 0)) * item.get("model_quantity_purchased", 1),
                "variation": item.get("model_name"),
                "image_url": item.get("image_info", {}).get("image_url"),
            })
        
        return NormalizedOrder(
            platform_order_id=raw_order.get("order_sn", ""),
            platform="shopee",
            
            customer_name=raw_order.get("buyer_username", ""),
            customer_phone=recipient.get("phone", ""),
            
            shipping_name=recipient.get("name", ""),
            shipping_phone=recipient.get("phone", ""),
            shipping_address=recipient.get("full_address", ""),
            shipping_district=recipient.get("district", ""),
            shipping_city=recipient.get("city", ""),
            shipping_province=recipient.get("state", ""),
            shipping_postal_code=recipient.get("zipcode", ""),
            shipping_country=recipient.get("region", "TH"),
            
            order_status=raw_order.get("order_status", ""),
            status_normalized=self.normalize_order_status(raw_order.get("order_status", "")),
            
            subtotal=float(raw_order.get("total_amount", 0)),
            shipping_fee=float(raw_order.get("actual_shipping_fee", 0)),
            total_amount=float(raw_order.get("total_amount", 0)),
            
            payment_method=raw_order.get("payment_method", ""),
            paid_at=datetime.fromtimestamp(raw_order["pay_time"]) if raw_order.get("pay_time") else None,
            
            shipping_method=raw_order.get("shipping_carrier", ""),
            tracking_number=raw_order.get("tracking_no"),
            courier=raw_order.get("shipping_carrier"),
            
            order_created_at=datetime.fromtimestamp(raw_order["create_time"]) if raw_order.get("create_time") else None,
            order_updated_at=datetime.fromtimestamp(raw_order["update_time"]) if raw_order.get("update_time") else None,
            
            items=items,
            raw_payload=raw_order,
        )
    
    def normalize_order_status(self, platform_status: str) -> str:
        """Map Shopee status to normalized status"""
        return self.STATUS_MAP.get(platform_status, "NEW")
    
    # ========== Webhooks ==========
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify Shopee webhook signature
        Signature = SHA256(url + payload + partner_key)
        """
        # Shopee webhook signature verification
        expected = hmac.new(
            self.app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Shopee webhook payload"""
        return {
            "event_type": payload.get("code"),  # 3 = order status update
            "order_id": payload.get("data", {}).get("ordersn"),
            "shop_id": str(payload.get("shop_id")),
            "timestamp": payload.get("timestamp"),
            "data": payload.get("data", {}),
        }
