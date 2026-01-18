"""
Master Tables: Company, Warehouse, SalesChannel, AppUser, Role
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core import Base
from .base import UUIDMixin, TimestampMixin

class Company(Base, UUIDMixin, TimestampMixin):
    """Company/Legal Entity"""
    __tablename__ = "company"
    
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    tax_id = Column(String(20))
    
    # Relationships
    warehouses = relationship("Warehouse", back_populates="company")
    orders = relationship("OrderHeader", back_populates="company")

class Warehouse(Base, UUIDMixin, TimestampMixin):
    """Warehouse"""
    __tablename__ = "warehouse"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    company = relationship("Company", back_populates="warehouses")
    orders = relationship("OrderHeader", back_populates="warehouse")
    stock_ledger = relationship("StockLedger", back_populates="warehouse")
    prepack_boxes = relationship("PrepackBox", back_populates="warehouse")

class SalesChannel(Base):
    """Sales Channel (Shopee, Lazada, TikTok, etc.)"""
    __tablename__ = "sales_channel"
    
    code = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    
    # Relationships
    orders = relationship("OrderHeader", back_populates="channel")

class Department(Base, UUIDMixin, TimestampMixin):
    """Department/แผนก"""
    __tablename__ = "department"
    
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)  # Store allowed_pages as JSON
    
    # Relationships
    users = relationship("AppUser", back_populates="department")

class Role(Base, UUIDMixin):
    """User Role"""
    __tablename__ = "role"
    
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role")

class AppUser(Base, UUIDMixin, TimestampMixin):
    """Application User"""
    __tablename__ = "app_user"
    
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200))
    full_name = Column(String(200))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("department.id"), nullable=True)
    
    # Relationships
    department = relationship("Department", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user")
    orders_created = relationship("OrderHeader", foreign_keys="OrderHeader.created_by", back_populates="creator")
    orders_sold = relationship("OrderHeader", foreign_keys="OrderHeader.sales_by", back_populates="sales_person")

class UserRole(Base):
    """User-Role Many-to-Many"""
    __tablename__ = "user_role"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), primary_key=True)
    
    # Relationships
    user = relationship("AppUser", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
