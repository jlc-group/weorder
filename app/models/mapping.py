from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class PlatformListing(Base, UUIDMixin, TimestampMixin):
    """
    Represents a sellable product listing on a specific platform (Shopee, Lazada, TikTok).
    This can be a single item or a bundle (set).
    It maps the Platform's SKU to one or more Master Products (Inventory).
    """
    __tablename__ = "platform_listing"
    
    platform = Column(String(50), nullable=False) # shopee, lazada, tiktok
    platform_sku = Column(String(100), nullable=False, index=True) # The SKU string from the channel
    name = Column(String(300)) # Name of the listing (optional, can sync from platform)
    
    # Relationships
    items = relationship("PlatformListingItem", back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('platform', 'platform_sku', name='uq_platform_sku'),
    )

class PlatformListingItem(Base, UUIDMixin):
    """
    Component of a Platform Listing.
    Maps a Listing to a Master Product with a quantity.
    """
    __tablename__ = "platform_listing_item"
    
    listing_id = Column(UUID(as_uuid=True), ForeignKey("platform_listing.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), nullable=False) # Link to Master Product
    quantity = Column(Integer, default=1, nullable=False)
    
    # Relationships
    listing = relationship("PlatformListing", back_populates="items")
    product = relationship("Product")
