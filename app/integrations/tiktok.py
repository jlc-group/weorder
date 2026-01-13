"""
TikTok Shop Open API Client - V2
API Documentation: https://partner.tiktokshop.com/docv2
"""
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta, timezone
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
        "AWAITING_COLLECTION": "READY_TO_SHIP",
        "IN_TRANSIT": "SHIPPED",
        "DELIVERED": "DELIVERED",
        "COMPLETED": "COMPLETED",
        "CANCELLED": "CANCELLED",
        "CANCELLATION_REQUESTED": "CANCELLED",
        # Return Statuses
        "BUYER_SHIPPED_ITEM": "RETURNED",
        "RETURN_OR_REFUND_REQUEST_COMPLETE": "RETURNED",
        "RETURN_OR_REFUND_REQUEST_CANCEL": "CANCELLED", # Or keep as DELIVERED if it was? But usually it stays in its previous state.
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
        # Use json.dumps only if body is not None (even if empty dict)
        body_str = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
        
        # Build sign string: secret + path + params + body + secret
        sign_string = f"{self.app_secret}{path}{params_string}{body_str}{self.app_secret}"
        
        # print(f"DEBUG SIGN: {sign_string}")
        
        # HMAC-SHA256
        signature = hmac.new(
            self.app_secret.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _fetch_shop_cipher(self):
        """Fetch shop cipher for the current shop_id"""
        if self.shop_cipher:
            return

        timestamp = int(time.time())
        path = "/authorization/202309/shops"
        
        params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
        }
        
        # Sign the request
        signature = self._generate_signature_v2(path, params)
        params["sign"] = signature
        
        url = f"{self.BASE_URL}{path}"
        
        async with httpx.AsyncClient() as client:
            headers = {
                "x-tts-access-token": self.access_token,
                "Content-Type": "application/json"
            }
            response = await client.get(url, params=params, headers=headers)
            data = response.json()
            
            if data.get("code") == 0:
                shops = data.get("data", {}).get("shops", [])
                for shop in shops:
                    if str(shop.get("id")) == self.shop_id:
                        self.shop_cipher = shop.get("cipher")
                        logger.info(f"Fetched shop_cipher for {self.shop_id}: {self.shop_cipher}")
                        break
            else:
                logger.error(f"Failed to fetch shops: {data}")

    async def _make_request(
        self,
        api_path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated API request - V2"""
        await self.ensure_valid_token()
        
        # Ensure we have shop_cipher
        if not self.shop_cipher:
            await self._fetch_shop_cipher()
        
        timestamp = int(time.time())
        
        # Build V2 API path - format: /order/202309/orders/search
        if api_path.startswith(("/order/", "/fulfillment/", "/product/", "/return/", "/finance/", "/reverse/", "/return_refund/")):
            full_path = api_path
        else:
            full_path = f"/order/{self.API_VERSION}/orders{api_path}"
        
        # V2 request params
        request_params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "shop_id": self.shop_id,
        }
        
        # Add extra params
        if params:
            request_params.update(params)
        
        if self.shop_cipher:
            request_params["shop_cipher"] = self.shop_cipher
        
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
        # Note: Token refresh uses auth domain, not API domain
        url = f"https://auth.tiktok-shops.com/api/v2/token/refresh"
        
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
            )
            
            self._log_api_call("GET", "/api/v2/token/refresh", response.status_code)
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
        # Use query params for page_size to match working reference
        params = {
            "page_size": min(page_size, 100),
            "sort_field": "create_time",
            "sort_order": "DESC",
        }
        
        body = {}
        
        if time_from:
            # Ensure UTC timezone if naive
            if time_from.tzinfo is None:
                # Assume UTC if naive, or convert to UTC if needed
                # Ideally, the input should already be UTC, but let's be safe
                pass 
            body["create_time_ge"] = int(time_from.timestamp())
        if time_to:
            if time_to.tzinfo is None:
                pass
            body["create_time_lt"] = int(time_to.timestamp())
        if status:
            body["order_status"] = status  # V2 uses string, not array
        if cursor:
            params["page_token"] = cursor # API uses page_token, internal cursor
            # Also support cursor param if API expects it
            params["cursor"] = cursor
        
        try:
            # If body is empty, send empty dict
            data = await self._make_request("/search", method="POST", params=params, body=body)
            print(f"DEBUG: TikTok Search Response: {json.dumps(data)}")
            orders = data.get("orders", [])
            
            
            next_cursor = data.get("next_cursor") or data.get("next_page_token")
            
            return {
                "orders": orders,
                "next_cursor": next_cursor,
                "total": data.get("total_count", len(orders)),
                "has_more": bool(next_cursor),
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
        API: GET /orders
        """
        try:
            # V2 API uses GET /orders with ids parameter
            params = {"ids": order_id}
            data = await self._make_request("", method="GET", params=params)
            orders = data.get("order_list", []) # V2 might return 'order_list' or 'orders'
            if not orders:
                 orders = data.get("orders", [])
            return orders[0] if orders else {}
        except Exception as e:
            logger.error(f"Error fetching TikTok order detail {order_id}: {e}")
            return {}

    async def get_order_details_batch(self, order_ids: list[str]) -> list[dict]:
        """
        Get details for multiple orders (Batch)
        Max 50 IDs per request
        """
        if not order_ids:
            return []
            
        try:
            # Join IDs with comma
            ids_str = ",".join(order_ids)
            params = {"ids": ids_str}
            
            data = await self._make_request("", method="GET", params=params)
            orders = data.get("order_list", [])
            if not orders:
                orders = data.get("orders", [])
                
            return orders
        except Exception as e:
            logger.error(f"Error fetching TikTok batch orders: {e}")
            return []
    async def get_shipping_label(self, order_id: str) -> str:
        """
        Get shipping label URL for an order
        """
        try:
            # 1. Get order detail to find package_id
            order_detail = await self.get_order_detail(order_id)
            if not order_detail:
                raise Exception("Order not found")
            
            packages = order_detail.get("packages", [])
            if not packages:
                raise Exception("No packages found for order")
            
            package_id = packages[0].get("id")
            
            # 2. Get shipping document URL
            # API: /fulfillment/202309/packages/{package_id}/shipping_documents
            path = f"/fulfillment/{self.API_VERSION}/packages/{package_id}/shipping_documents"
            
            params = {
                "document_type": "SHIPPING_LABEL",
                "document_size": "A6", # Default to A6
            }
            
            data = await self._make_request(path.replace(f"/order/{self.API_VERSION}/orders", ""), params=params)
            
            # Response should contain doc_url
            return data.get("doc_url")
            
        except Exception as e:
            logger.error(f"Error getting TikTok label for {order_id}: {e}")
            return None

    async def ship_package(self, package_id: str, handover_method: str = "DROP_OFF") -> bool:
        """
        Ship package (Arrange Shipment / RTS)
        handover_method: DROP_OFF or PICKUP
        """
        try:
            # API: /fulfillment/202309/packages/{package_id}/ship
            path = f"/fulfillment/{self.API_VERSION}/packages/{package_id}/ship"
            
            # Remove /order/... prefix logic from make_request by passing absolute-ish path handling
            # _make_request logic: if api_path starts with /fulfillment ... use fully qualified?
            # Existing logic: if api_path.startswith(("/order/", "/fulfillment/")): full_path = api_path
            # So passing /fulfillment/... works.
            
            body = {
                "handover_method": handover_method
            }
            
            await self._make_request(path, method="POST", body=body)
            return True
            
        except Exception as e:
            logger.error(f"Error shipping package {package_id}: {e}")
            raise e
    
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
                "unit_price": float(item.get("sale_price", 0)),
                "total_price": float(item.get("sale_price", 0)) * item.get("quantity", 1),
                "variation": item.get("sku_name"),
                "image_url": item.get("sku_image"),
            })
        
        # Calculate totals
        payment = raw_order.get("payment", {})
        total_amount = float(payment.get("total_amount", 0))
        shipping_fee = float(payment.get("shipping_fee", 0))
        
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
            
            payment_method=raw_order.get("payment_method_name", "UNKNOWN"),
            payment_status="PAID" if self.normalize_order_status(raw_order.get("status", "")) in ["PAID", "PACKING", "SHIPPED", "DELIVERED", "COMPLETED"] else "PENDING",
            
            tracking_number=raw_order.get("packages", [{}])[0].get("tracking_number") if raw_order.get("packages") else None,
            courier=raw_order.get("packages", [{}])[0].get("shipping_provider_name") if raw_order.get("packages") else None,
            
            order_created_at=datetime.fromtimestamp(raw_order["create_time"], timezone.utc) if raw_order.get("create_time") else None,
            order_updated_at=datetime.fromtimestamp(raw_order["update_time"], timezone.utc) if raw_order.get("update_time") else None,
            
            shipped_at=(
                datetime.fromtimestamp(raw_order["collection_time"], timezone.utc) if raw_order.get("collection_time")
                else None
            ),
            
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

    async def get_statements(self, start_time: datetime, end_time: datetime, cursor: str = None, page_size: int = 20) -> Dict:
        """
        Get finance statements from TikTok Finance API
        Statements are settled daily and contain financial breakdown per order.
        
        Docs: /finance/202309/statements
        """
        path = f"/finance/{self.API_VERSION}/statements"
        
        params = {
            "statement_time_ge": int(start_time.timestamp()),
            "statement_time_lt": int(end_time.timestamp()),
            "page_size": page_size,
            "sort_field": "statement_time", 
            "sort_order": "DESC",
        }
        if cursor:
            params["page_token"] = cursor
            
        resp = await self._make_request(path, method="GET", params=params)
        print(f"DEBUG: TikTok Statements Response: {json.dumps(resp)}")
        return resp

    async def get_statement_transactions(self, statement_id: str, cursor: str = None, page_size: int = 50) -> Dict:
        """
        Get transactions for a specific statement.
        
        Docs: /finance/202309/statements/{statement_id}/statement_transactions
        """
        path = f"/finance/{self.API_VERSION}/statements/{statement_id}/statement_transactions"
        
        params = {
            "page_size": page_size,
            "sort_field": "order_create_time", # API Requires this specific field
            "sort_order": "DESC",
        }
        if cursor:
            params["page_token"] = cursor
            
        resp = await self._make_request(path, method="GET", params=params)
        return resp

    async def get_payments(self, start_time: datetime, end_time: datetime, cursor: str = None, page_size: int = 20) -> Dict:
        """
        Get payments (bank transfers) - for reconciliation.
        
        Docs: /finance/202309/payments
        """
        path = f"/finance/{self.API_VERSION}/payments"
        
        params = {
            "request_time_ge": int(start_time.timestamp()),
            "request_time_lt": int(end_time.timestamp()),
            "page_size": page_size,
        }
        if cursor:
            params["page_token"] = cursor
            
        resp = await self._make_request(path, method="GET", params=params)
        print(f"DEBUG: TikTok Payments Response: {json.dumps(resp)}")
        return resp

    async def get_reverse_orders(self, update_time_from: datetime, update_time_to: datetime, cursor: str = None, page_size: int = 50) -> Dict:
        """
        Get reverse orders (Returns/Refunds/Cancellations)
        API V2: /return_refund/202309/returns/search and cancellations/search
        """
        combined_items = []
        
        # 1. Fetch Returns with Pagination
        page_token = ""
        while True:
            body = {
                "page_size": page_size,
                "update_time_ge": int(update_time_from.timestamp()),
                "update_time_lt": int(update_time_to.timestamp()),
            }
            if page_token:
                body["page_token"] = page_token
                
            try:
                print(f"DEBUG: Fetching returns page (token: {page_token})...")
                resp = await self._make_request("/return_refund/202309/returns/search", method="POST", body=body)
                returns = resp.get("return_orders", [])
                print(f"DEBUG: Found {len(returns)} returns on this page")
                for r in returns:
                    r["return_status"] = r.get("return_status")
                    combined_items.append(r)
                
                page_token = resp.get("next_page_token")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching TikTok returns: {e}")
                break

        # 2. Fetch Cancellations with Pagination
        page_token = ""
        while True:
            body = {
                "page_size": page_size,
                "update_time_ge": int(update_time_from.timestamp()),
                "update_time_lt": int(update_time_to.timestamp()),
            }
            if page_token:
                body["page_token"] = page_token

            try:
                print(f"DEBUG: Fetching cancellations page (token: {page_token})...")
                resp = await self._make_request("/return_refund/202309/cancellations/search", method="POST", body=body)
                cancellations = resp.get("cancellations", [])
                print(f"DEBUG: Found {len(cancellations)} cancellations on this page")
                for c in cancellations:
                    c["return_status"] = c.get("cancel_status")
                    combined_items.append(c)
                
                page_token = resp.get("next_page_token")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching TikTok cancellations: {e}")
                break
        
        return {
            "returns": combined_items,
            "next_page_token": None 
        }
