"""
Base Platform Client - Abstract base class for marketplace integrations
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class NormalizedOrder:
    """
    Normalized order structure that all platforms map to
    """
    # Identifiers
    platform_order_id: str
    platform: str  # shopee, lazada, tiktok
    
    # Customer Info
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    
    # Shipping Address
    shipping_name: str = ""
    shipping_phone: str = ""
    shipping_address: str = ""
    shipping_district: str = ""
    shipping_city: str = ""
    shipping_province: str = ""
    shipping_postal_code: str = ""
    shipping_country: str = "TH"
    
    # Order Details
    order_status: str = "NEW"  # Raw status from platform
    status_normalized: str = "NEW"  # Normalized: NEW, WAIT_PAY, PAID, PACKING, SHIPPED, DELIVERED, RETURNED, CANCELLED
    
    # Amounts
    subtotal: float = 0.0
    shipping_fee: float = 0.0
    discount_amount: float = 0.0
    total_amount: float = 0.0
    
    # Payment
    payment_method: str = ""
    payment_status: str = ""
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    
    # Shipping
    shipping_method: str = ""
    tracking_number: Optional[str] = None
    courier: Optional[str] = None
    
    # Timestamps
    order_created_at: Optional[datetime] = None
    order_updated_at: Optional[datetime] = None
    
    # Items
    items: List[Dict[str, Any]] = None
    
    # Raw data
    raw_payload: Dict[str, Any] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.raw_payload is None:
            self.raw_payload = {}


@dataclass
class NormalizedOrderItem:
    """
    Normalized order item structure
    """
    platform_item_id: str
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    discount_amount: float = 0.0
    variation: Optional[str] = None
    image_url: Optional[str] = None


class BasePlatformClient(ABC):
    """
    Abstract base class for marketplace platform integrations
    """
    PLATFORM_NAME: str = "base"
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        shop_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_id = shop_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._token_expires_at: Optional[datetime] = None
    
    # ========== Authentication ==========
    
    @abstractmethod
    async def get_auth_url(self, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL for shop to authorize
        """
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        Returns: {access_token, refresh_token, expires_in}
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        Returns: {access_token, refresh_token, expires_in}
        """
        pass
    
    def is_token_expired(self) -> bool:
        """Check if current access token is expired"""
        if not self._token_expires_at:
            return True
        # Add 5 minute buffer
        return datetime.utcnow() >= (self._token_expires_at - timedelta(minutes=5))
    
    async def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refresh if needed"""
        if self.is_token_expired() and self.refresh_token:
            try:
                result = await self.refresh_access_token()
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token", self.refresh_token)
                expires_in = result.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                return True
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return False
        return True
    
    # ========== Orders ==========
    
    @abstractmethod
    async def get_orders(
        self,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        status: Optional[str] = None,
        cursor: Optional[str] = None,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Get list of orders from platform
        Returns: {orders: List[Dict], next_cursor: Optional[str], total: int}
        """
        pass
    
    @abstractmethod
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed order information
        """
        pass
    
    @abstractmethod
    def normalize_order(self, raw_order: Dict[str, Any]) -> NormalizedOrder:
        """
        Convert platform-specific order format to normalized format
        """
        pass
    
    @abstractmethod
    def normalize_order_status(self, platform_status: str) -> str:
        """
        Map platform-specific status to normalized status
        """
        pass
    
    # ========== Webhooks ==========
    
    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook request signature
        """
        pass
    
    @abstractmethod
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse webhook payload and extract event type and data
        Returns: {event_type: str, order_id: str, data: Dict}
        """
        pass
    
    # ========== Product & Stock (Optional) ==========
    
    async def get_products(self, cursor: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
        """Get products from platform (optional implementation)"""
        raise NotImplementedError("Product sync not implemented for this platform")
    
    async def update_stock(self, sku: str, quantity: int) -> bool:
        """Update stock on platform (optional implementation)"""
        raise NotImplementedError("Stock sync not implemented for this platform")
    
    # ========== Utilities ==========
    
    def _build_headers(self) -> Dict[str, str]:
        """Build common request headers"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}" if self.access_token else "",
        }
    
    def _log_api_call(self, method: str, endpoint: str, status_code: int):
        """Log API call for debugging"""
        logger.info(f"[{self.PLATFORM_NAME}] {method} {endpoint} -> {status_code}")
