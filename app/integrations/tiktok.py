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
                # Manually serialize body to match signature generation
                # json.dumps with separators=(',', ':') removes whitespace
                content = json.dumps(body, separators=(',', ':'), sort_keys=True) if body is not None else ""
                response = await client.post(url, params=request_params, content=content, headers=headers)
            
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
        use_update_time: bool = False,  # NEW: For incremental sync
    ) -> Dict[str, Any]:
        """
        Get list of orders from TikTok Shop - V2 API
        API: /orders/search
        
        Args:
            use_update_time: If True, filter by update_time instead of create_time.
                            This catches orders that changed status, not just new orders.
                            Use for incremental sync to reduce API calls.
        """
        # Use query params for page_size to match working reference
        params = {
            "page_size": min(page_size, 100),
            "sort_field": "update_time" if use_update_time else "create_time",
            "sort_order": "DESC",
        }
        
        body = {}
        
        # Choose time filter based on mode
        if use_update_time:
            # INCREMENTAL MODE: Filter by update_time to catch status changes
            if time_from:
                body["update_time_ge"] = int(time_from.timestamp())
            if time_to:
                body["update_time_lt"] = int(time_to.timestamp())
            logger.info(f"TikTok get_orders: INCREMENTAL mode (update_time filter)")
        else:
            # FULL SYNC MODE: Filter by create_time (original behavior)
            if time_from:
                body["create_time_ge"] = int(time_from.timestamp())
            if time_to:
                body["create_time_lt"] = int(time_to.timestamp())
        
        if status:
            # V2 API typically prefers order_status_list for filtering
            # Even if single status, send as list
            body["order_status_list"] = [status]
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
                "more": bool(next_cursor),
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
        
        # Parse items and consolidate duplicates by SKU
        items_by_sku: Dict[str, Any] = {}
        for item in raw_order.get("line_items", []):
            sku = item.get("seller_sku", "")
            quantity = item.get("quantity", 1)
            sale_price = float(item.get("sale_price", 0))
            
            if sku in items_by_sku:
                # Merge with existing item
                items_by_sku[sku]["quantity"] += quantity
                items_by_sku[sku]["total_price"] += sale_price * quantity
            else:
                items_by_sku[sku] = {
                    "platform_item_id": str(item.get("id")),
                    "sku": sku,
                    "product_name": item.get("product_name", ""),
                    "quantity": quantity,
                    "unit_price": sale_price,
                    "total_price": sale_price * quantity,
                    "variation": item.get("sku_name"),
                    "image_url": item.get("sku_image"),
                }
        
        items = list(items_by_sku.values())
        
        # Calculate totals
        payment = raw_order.get("payment", {})
        total_amount = float(payment.get("total_amount", 0))
        shipping_fee = float(payment.get("shipping_fee", 0))
        
        # Check if this is an affiliate order
        # Note: TikTok order detail API doesn't provide direct affiliate/live info
        # This will be updated later from finance transaction data
        # For now, we set it based on available indicators
        is_affiliate = False
        is_live = False

        # Check if order has live_tag or other indicators
        # This is a placeholder - actual detection requires finance data
        live_tag = raw_order.get("live_tag")
        if live_tag:
            is_live = True

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
            status_normalized=self._normalize_status_with_reason(raw_order),

            subtotal=total_amount - shipping_fee,
            shipping_fee=shipping_fee,
            total_amount=total_amount,

            payment_method=raw_order.get("payment_method_name", "UNKNOWN"),
            payment_status="PAID" if self.normalize_order_status(raw_order.get("status", "")) in ["PAID", "PACKING", "SHIPPED", "DELIVERED", "COMPLETED"] else "PENDING",

            tracking_number=(
                raw_order.get("packages", [{}])[0].get("tracking_number") 
                if raw_order.get("packages") and raw_order.get("packages", [{}])[0].get("tracking_number")
                else None
            ),
            # TikTok sends courier in "shipping_provider" (top-level), not packages[0].shipping_provider_name
            courier=(
                raw_order.get("shipping_provider")  # Primary: top-level field
                or (raw_order.get("packages", [{}])[0].get("shipping_provider_name") if raw_order.get("packages") else None)  # Fallback
            ),

            order_created_at=datetime.fromtimestamp(raw_order["create_time"], timezone.utc) if raw_order.get("create_time") else None,
            order_updated_at=datetime.fromtimestamp(raw_order["update_time"], timezone.utc) if raw_order.get("update_time") else None,

            shipped_at=(
                datetime.fromtimestamp(raw_order["collection_time"], timezone.utc) if raw_order.get("collection_time")
                else None
            ),

            is_affiliate_order=is_affiliate,
            is_live_order=is_live,

            items=items,
            raw_payload=raw_order,
        )
    

    def _normalize_status_with_reason(self, raw_order: Dict[str, Any]) -> str:
        """Normalize status with checks for cancellation reason"""
        status = raw_order.get("status", "")
        normalized = self.STATUS_MAP.get(status, "NEW")
        
        # Check for Delivery Failed / Customer Rejected
        # TikTok status might be CANCELLED with reason
        if normalized in ["CANCELLED", "RETURNED"]:
            reason = (raw_order.get("cancel_reason") or "").lower()
            
            # Keywords indicating delivery failure / rejection
            fail_keywords = [
                "delivery failed", 
                "package returned",
                "logistics_process_failed",
                "buyer_refused",
                "recipient rejected",
                "customer rejected",
                "undeliverable",
                "delivery unsuccessful",
                "lost",
                "attempted failed"
            ]
            
            if any(k in reason for k in fail_keywords):
                return "DELIVERY_FAILED"

            # Thai keywords
            thai_keywords = [
                "ส่งไม่สำเร็จ",
                "ปฏิเสธ",
                "ติดต่อไม่ได้",
                "หาไม่เจอ",
                "ตีกลับ"
            ]
            if any(k in reason for k in thai_keywords):
                return "DELIVERY_FAILED"
                
        return normalized

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

    async def get_order_transactions(self, order_id: str) -> Dict:
        """
        Get SKU-level transaction details for a specific order.
        Uses API version 202501 for detailed fee breakdown including:
        - ค่าธรรมเนียมคำสั่งซื้อ (transaction_fee_amount)
        - ค่าบริการแบรนด์ดัง/แฟลชเซล (flash_sales_service_fee_amount)
        - ค่าธรรมเนียมสนับสนุนการเติบโต (dynamic_commission_amount)
        - ค่าธรรมเนียมโครงสร้างพื้นฐาน (vn_fix_infrastructure_fee)
        
        Docs: /finance/202501/orders/{order_id}/statement_transactions
        """
        # Use API version 202501 for more detailed fee breakdown
        path = f"/finance/202501/orders/{order_id}/statement_transactions"
        
        params = {
            "page_size": 50,
        }
        
        try:
            resp = await self._make_request(path, method="GET", params=params)
            logger.info(f"TikTok Order Statement Transactions (v202501) for {order_id}")
            return resp
        except Exception as e:
            logger.error(f"Error fetching order statement transactions for {order_id}: {e}")
            # Fallback to old API version if 202501 fails
            try:
                path_old = f"/finance/{self.API_VERSION}/orders/{order_id}/statement_transactions"
                resp = await self._make_request(path_old, method="GET", params=params)
                return resp
            except:
                return {}

    async def get_reverse_orders(self, update_time_from: datetime, update_time_to: datetime, cursor: str = None, page_size: int = 50) -> Dict:
        """
        Get reverse orders (Returns/Refunds/Cancellations)
        API V2: /return_refund/202309/returns/search and cancellations/search
        
        Note: This function handles pagination internally and returns ALL results.
        Caller should NOT loop over this function.
        """
        combined_items = []
        MAX_PAGES = 20  # Safety limit to prevent infinite loops
        
        # 1. Fetch Returns with Pagination
        page_token = ""
        seen_tokens = set()  # Track tokens to detect loops
        page_count = 0
        
        while page_count < MAX_PAGES:
            page_count += 1
            body = {
                "page_size": page_size,
                "update_time_ge": int(update_time_from.timestamp()),
                "update_time_lt": int(update_time_to.timestamp()),
            }
            if page_token:
                # Check for duplicate token (indicates API bug/loop)
                if page_token in seen_tokens:
                    logger.warning(f"Detected duplicate page_token in returns, breaking loop")
                    break
                seen_tokens.add(page_token)
                body["page_token"] = page_token
                
            try:
                logger.debug(f"Fetching returns page {page_count} (token: {page_token[:20] if page_token else 'None'}...)")
                resp = await self._make_request("/return_refund/202309/returns/search", method="POST", body=body)
                returns = resp.get("return_orders", [])
                logger.debug(f"Found {len(returns)} returns on page {page_count}")
                
                for r in returns:
                    r["return_status"] = r.get("return_status")
                    combined_items.append(r)
                
                page_token = resp.get("next_page_token", "")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching TikTok returns: {e}")
                break
        
        if page_count >= MAX_PAGES:
            logger.warning(f"Hit MAX_PAGES limit ({MAX_PAGES}) for returns, some data may be missing")

        # 2. Fetch Cancellations with Pagination
        page_token = ""
        seen_tokens = set()
        page_count = 0
        
        while page_count < MAX_PAGES:
            page_count += 1
            body = {
                "page_size": page_size,
                "update_time_ge": int(update_time_from.timestamp()),
                "update_time_lt": int(update_time_to.timestamp()),
            }
            if page_token:
                if page_token in seen_tokens:
                    logger.warning(f"Detected duplicate page_token in cancellations, breaking loop")
                    break
                seen_tokens.add(page_token)
                body["page_token"] = page_token

            try:
                logger.debug(f"Fetching cancellations page {page_count} (token: {page_token[:20] if page_token else 'None'}...)")
                resp = await self._make_request("/return_refund/202309/cancellations/search", method="POST", body=body)
                cancellations = resp.get("cancellations", [])
                logger.debug(f"Found {len(cancellations)} cancellations on page {page_count}")
                
                for c in cancellations:
                    c["return_status"] = c.get("cancel_status")
                    combined_items.append(c)
                
                page_token = resp.get("next_page_token", "")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching TikTok cancellations: {e}")
                break
        
        if page_count >= MAX_PAGES:
            logger.warning(f"Hit MAX_PAGES limit ({MAX_PAGES}) for cancellations, some data may be missing")
        
        logger.info(f"get_reverse_orders: Total {len(combined_items)} items (returns + cancellations)")
        return {
            "returns": combined_items,
            "next_page_token": None 
        }

    # ========== Affiliate / Creator APIs ==========
    
    async def get_affiliate_orders(
        self, 
        time_from: datetime, 
        time_to: datetime, 
        cursor: str = None, 
        page_size: int = 50
    ) -> Dict:
        """
        Get affiliate orders - orders from creator content (video, live, showcase)
        
        API: /affiliate/202309/orders/search
        
        Returns orders with:
        - affiliate_commission_rate
        - creator_id  
        - content_type (VIDEO, LIVE, SHOWCASE)
        """
        path = f"/affiliate/{self.API_VERSION}/orders/search"
        
        body = {
            "create_time_ge": int(time_from.timestamp()),
            "create_time_lt": int(time_to.timestamp()),
            "page_size": min(page_size, 50),
        }
        if cursor:
            body["page_token"] = cursor
            
        try:
            resp = await self._make_request(path, method="POST", body=body)
            logger.info(f"TikTok Affiliate Orders: {len(resp.get('orders', []))} found")
            return resp
        except Exception as e:
            logger.error(f"Error fetching affiliate orders: {e}")
            # Return empty if API not available (may need beta access)
            return {"orders": [], "next_page_token": None}

    async def get_affiliate_creators(self, cursor: str = None, page_size: int = 20) -> Dict:
        """
        Get list of affiliate creators promoting our products
        
        API: /affiliate/202309/open_collaborations/creators/search
        """
        path = f"/affiliate/{self.API_VERSION}/open_collaborations/creators/search"
        
        body = {
            "page_size": min(page_size, 20),
        }
        if cursor:
            body["page_token"] = cursor
            
        try:
            resp = await self._make_request(path, method="POST", body=body)
            return resp
        except Exception as e:
            logger.error(f"Error fetching affiliate creators: {e}")
            return {"creators": [], "next_page_token": None}

    async def get_creator_performance(self, creator_id: str, days: int = 30) -> Dict:
        """
        Get creator performance statistics
        
        API: /affiliate/202309/creators/{creator_id}/performance
        
        Returns:
        - video_gmv: ยอดขายจากวิดีโอ
        - live_gmv: ยอดขายจาก live
        - showcase_gmv: ยอดขายจาก showcase
        - total_orders: จำนวน orders ทั้งหมด
        - commission_earned: ค่าคอมมิชชั่นที่ได้
        """
        path = f"/affiliate/{self.API_VERSION}/creators/{creator_id}/performance"
        
        params = {
            "days": days,
        }
        
        try:
            resp = await self._make_request(path, method="GET", params=params)
            return resp
        except Exception as e:
            logger.error(f"Error fetching creator performance for {creator_id}: {e}")
            return {}

    async def get_product_creatives(self, product_id: str, cursor: str = None, page_size: int = 20) -> Dict:
        """
        Get creatives (video/live content) for a specific product
        
        API: /affiliate/202309/products/{product_id}/creatives
        
        Returns creative count and details by SKU - useful for:
        - จำนวน creative by SKU
        - Video vs Live breakdown
        """
        path = f"/affiliate/{self.API_VERSION}/products/{product_id}/creatives"
        
        params = {
            "page_size": min(page_size, 20),
        }
        if cursor:
            params["page_token"] = cursor
            
        try:
            resp = await self._make_request(path, method="GET", params=params)
            return resp
        except Exception as e:
            logger.error(f"Error fetching product creatives for {product_id}: {e}")
            return {"creatives": [], "next_page_token": None}

    async def get_gmv_breakdown(self, time_from: datetime, time_to: datetime) -> Dict:
        """
        Get GMV breakdown by content type (Video, Live, Showcase, Other)
        
        Uses Finance Statement Transactions to calculate:
        - video_gmv: ยอดขายจากวิดีโอ
        - live_gmv: ยอดขายจาก live  
        - affiliate_commission: ค่าคอมมิชชั่น creator ทั้งหมด
        - direct_gmv: ยอดขายตรง (ไม่ผ่าน affiliate)
        
        Note: This aggregates data from statement_transactions which has
        affiliate_commission_amount field.
        """
        result = {
            "video_gmv": 0,
            "live_gmv": 0,
            "showcase_gmv": 0,
            "direct_gmv": 0,
            "total_gmv": 0,
            "affiliate_commission": 0,
            "orders_by_type": {
                "video": 0,
                "live": 0,
                "showcase": 0,
                "direct": 0
            }
        }
        
        try:
            # Get statements for the period
            statements_resp = await self.get_statements(time_from, time_to)
            statements = statements_resp.get("statements", [])
            
            for statement in statements:
                statement_id = statement.get("id")
                if not statement_id:
                    continue
                    
                # Get transactions for each statement
                txn_resp = await self.get_statement_transactions(statement_id)
                transactions = txn_resp.get("statement_transactions", [])
                
                for txn in transactions:
                    order_amount = float(txn.get("order_amount", 0))
                    affiliate_commission = float(txn.get("affiliate_commission_amount", 0))
                    
                    # Determine content type from transaction
                    # TikTok transaction has "sale_type" or similar indicator
                    sale_type = txn.get("sale_type", "").upper()
                    
                    if "VIDEO" in sale_type:
                        result["video_gmv"] += order_amount
                        result["orders_by_type"]["video"] += 1
                    elif "LIVE" in sale_type:
                        result["live_gmv"] += order_amount
                        result["orders_by_type"]["live"] += 1
                    elif "SHOWCASE" in sale_type or affiliate_commission > 0:
                        result["showcase_gmv"] += order_amount
                        result["orders_by_type"]["showcase"] += 1
                    else:
                        result["direct_gmv"] += order_amount
                        result["orders_by_type"]["direct"] += 1
                    
                    result["total_gmv"] += order_amount
                    result["affiliate_commission"] += affiliate_commission
            
            logger.info(f"TikTok GMV Breakdown: Video={result['video_gmv']}, Live={result['live_gmv']}, Total={result['total_gmv']}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating GMV breakdown: {e}")
            return result

    async def get_sku_creative_count(self) -> Dict:
        """
        Get creative count grouped by SKU
        
        Returns: {sku: {"video_count": X, "live_count": Y, "total_orders": Z}}
        
        Uses affiliate orders to aggregate by SKU.
        """
        result = {}
        
        try:
            # Get affiliate orders from last 30 days
            time_to = datetime.now(timezone.utc)
            time_from = time_to - timedelta(days=30)
            
            cursor = None
            while True:
                resp = await self.get_affiliate_orders(time_from, time_to, cursor)
                orders = resp.get("orders", [])
                
                for order in orders:
                    content_type = order.get("content_type", "UNKNOWN").upper()
                    
                    for item in order.get("line_items", []):
                        sku = item.get("seller_sku", "UNKNOWN")
                        
                        if sku not in result:
                            result[sku] = {
                                "video_count": 0,
                                "live_count": 0,
                                "showcase_count": 0,
                                "total_orders": 0,
                                "total_revenue": 0
                            }
                        
                        result[sku]["total_orders"] += 1
                        result[sku]["total_revenue"] += float(item.get("sale_price", 0))
                        
                        if "VIDEO" in content_type:
                            result[sku]["video_count"] += 1
                        elif "LIVE" in content_type:
                            result[sku]["live_count"] += 1
                        else:
                            result[sku]["showcase_count"] += 1
                
                cursor = resp.get("next_page_token")
                if not cursor:
                    break
            
            logger.info(f"TikTok SKU Creative Count: {len(result)} SKUs found")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating SKU creative count: {e}")
            return result
