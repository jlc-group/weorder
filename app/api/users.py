"""
Users and Roles API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
import uuid

from app.core import get_db
from app.models import AppUser, Role, UserRole, Department

router = APIRouter(prefix="/users", tags=["users"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])
departments_router = APIRouter(prefix="/departments", tags=["departments"])

# ============== Schemas ==============

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: Optional[str] = None
    role_ids: List[str] = []
    department_id: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    department_id: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    roles: List[dict] = []

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    allowed_pages: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_pages: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: UUID
    allowed_pages: List[str] = []

    class Config:
        from_attributes = True

class AssignRolesRequest(BaseModel):
    role_ids: List[str]

# Department schemas
class DepartmentBase(BaseModel):
    code: str
    name: str

class DepartmentCreate(DepartmentBase):
    allowed_pages: List[str] = []

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    allowed_pages: Optional[List[str]] = None

# ============== Available Pages ==============

AVAILABLE_PAGES = [
    {"key": "dashboard", "name": "Dashboard", "icon": "bi-speedometer2"},
    {"key": "orders", "name": "ออเดอร์", "icon": "bi-receipt"},
    {"key": "returns", "name": "สินค้าตีคืน", "icon": "bi-arrow-return-left"},
    {"key": "products", "name": "สินค้า", "icon": "bi-box"},
    {"key": "bundles", "name": "Platform Bundles", "icon": "bi-diagram-3"},
    {"key": "stock", "name": "สต๊อก", "icon": "bi-stack"},
    {"key": "outbound", "name": "รายงานส่งสินค้า", "icon": "bi-truck"},
    {"key": "packing", "name": "แพ็คสินค้า", "icon": "bi-box2"},
    {"key": "promotions", "name": "โปรโมชั่น", "icon": "bi-gift"},
    {"key": "finance", "name": "การเงิน", "icon": "bi-cash-stack"},
    {"key": "invoice", "name": "ใบกำกับภาษี", "icon": "bi-receipt-cutoff"},
    {"key": "settings", "name": "ตั้งค่า", "icon": "bi-plug"},
    {"key": "admin", "name": "จัดการผู้ใช้", "icon": "bi-shield-lock"},
]

# ============== Users Endpoints ==============

@router.get("", response_model=List[dict])
def list_users(db: Session = Depends(get_db)):
    """List all users with their roles and department"""
    users = db.query(AppUser).all()
    result = []
    for user in users:
        roles = [{"id": str(ur.role.id), "code": ur.role.code, "name": ur.role.name} 
                 for ur in user.user_roles if ur.role]
        dept = None
        if user.department:
            dept = {"id": str(user.department.id), "code": user.department.code, "name": user.department.name}
        result.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "roles": roles,
            "department": dept
        })
    return result

@router.post("", response_model=dict)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if username exists
    existing = db.query(AppUser).filter(AppUser.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash password if provided
    from app.api.auth import get_password_hash
    hashed_pw = None
    if user.password:
        hashed_pw = get_password_hash(user.password)
    
    # Create user
    dept_id = None
    if user.department_id:
        try:
            dept_id = uuid.UUID(user.department_id)
        except:
            pass
    
    new_user = AppUser(
        id=uuid.uuid4(),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        hashed_password=hashed_pw,
        department_id=dept_id
    )
    db.add(new_user)
    db.flush()
    
    # Assign roles
    for role_id in user.role_ids:
        try:
            role_uuid = uuid.UUID(role_id)
            role = db.query(Role).filter(Role.id == role_uuid).first()
            if role:
                user_role = UserRole(user_id=new_user.id, role_id=role.id)
                db.add(user_role)
        except:
            pass
    
    db.commit()
    
    return {"id": str(new_user.id), "username": new_user.username, "message": "User created"}

@router.put("/{user_id}", response_model=dict)
def update_user(user_id: str, user: UserUpdate, db: Session = Depends(get_db)):
    """Update a user"""
    try:
        uid = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    db_user = db.query(AppUser).filter(AppUser.id == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email is not None:
        db_user.email = user.email
    if user.full_name is not None:
        db_user.full_name = user.full_name
    if user.is_active is not None:
        db_user.is_active = user.is_active
    if user.department_id is not None:
        try:
            db_user.department_id = uuid.UUID(user.department_id) if user.department_id else None
        except:
            pass
    
    db.commit()
    return {"id": str(db_user.id), "message": "User updated"}

@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user"""
    try:
        uid = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    db_user = db.query(AppUser).filter(AppUser.id == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user roles first
    db.query(UserRole).filter(UserRole.user_id == uid).delete()
    db.delete(db_user)
    db.commit()
    
    return {"message": "User deleted"}

@router.post("/{user_id}/roles")
def assign_roles(user_id: str, request: AssignRolesRequest, db: Session = Depends(get_db)):
    """Assign roles to a user"""
    try:
        uid = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    db_user = db.query(AppUser).filter(AppUser.id == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove existing roles
    db.query(UserRole).filter(UserRole.user_id == uid).delete()
    
    # Add new roles
    for role_id in request.role_ids:
        try:
            role_uuid = uuid.UUID(role_id)
            role = db.query(Role).filter(Role.id == role_uuid).first()
            if role:
                user_role = UserRole(user_id=uid, role_id=role.id)
                db.add(user_role)
        except:
            pass
    
    db.commit()
    return {"message": "Roles assigned"}

# ============== Roles Endpoints ==============

@roles_router.get("", response_model=List[dict])
def list_roles(db: Session = Depends(get_db)):
    """List all roles"""
    roles = db.query(Role).all()
    result = []
    for role in roles:
        # Parse allowed_pages from description (stored as JSON string)
        allowed_pages = []
        if role.description and role.description.startswith("["):
            try:
                import json
                allowed_pages = json.loads(role.description)
            except:
                pass
        
        result.append({
            "id": str(role.id),
            "code": role.code,
            "name": role.name,
            "allowed_pages": allowed_pages
        })
    return result

@roles_router.post("", response_model=dict)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    """Create a new role"""
    import json
    
    existing = db.query(Role).filter(Role.code == role.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    new_role = Role(
        id=uuid.uuid4(),
        code=role.code,
        name=role.name,
        description=json.dumps(role.allowed_pages)  # Store pages as JSON in description
    )
    db.add(new_role)
    db.commit()
    
    return {"id": str(new_role.id), "code": new_role.code, "message": "Role created"}

@roles_router.put("/{role_id}", response_model=dict)
def update_role(role_id: str, role: RoleUpdate, db: Session = Depends(get_db)):
    """Update a role"""
    import json
    
    try:
        rid = uuid.UUID(role_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid role ID")
    
    db_role = db.query(Role).filter(Role.id == rid).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.name is not None:
        db_role.name = role.name
    if role.allowed_pages is not None:
        db_role.description = json.dumps(role.allowed_pages)
    
    db.commit()
    return {"id": str(db_role.id), "message": "Role updated"}

@roles_router.delete("/{role_id}")
def delete_role(role_id: str, db: Session = Depends(get_db)):
    """Delete a role"""
    try:
        rid = uuid.UUID(role_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid role ID")
    
    db_role = db.query(Role).filter(Role.id == rid).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Delete user roles first
    db.query(UserRole).filter(UserRole.role_id == rid).delete()
    db.delete(db_role)
    db.commit()
    
    return {"message": "Role deleted"}

@roles_router.get("/pages")
def get_available_pages():
    """Get list of available pages for permissions"""
    return AVAILABLE_PAGES

# ============== Departments Endpoints ==============

@departments_router.get("", response_model=List[dict])
def list_departments(db: Session = Depends(get_db)):
    """List all departments"""
    import json
    departments = db.query(Department).all()
    result = []
    for dept in departments:
        allowed_pages = []
        if dept.description and dept.description.startswith("["):
            try:
                allowed_pages = json.loads(dept.description)
            except:
                pass
        result.append({
            "id": str(dept.id),
            "code": dept.code,
            "name": dept.name,
            "allowed_pages": allowed_pages
        })
    return result

@departments_router.post("", response_model=dict)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db)):
    """Create a new department"""
    import json
    
    existing = db.query(Department).filter(Department.code == dept.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    
    new_dept = Department(
        id=uuid.uuid4(),
        code=dept.code,
        name=dept.name,
        description=json.dumps(dept.allowed_pages)
    )
    db.add(new_dept)
    db.commit()
    
    return {"id": str(new_dept.id), "code": new_dept.code, "message": "Department created"}

@departments_router.put("/{dept_id}", response_model=dict)
def update_department(dept_id: str, dept: DepartmentUpdate, db: Session = Depends(get_db)):
    """Update a department"""
    import json
    
    try:
        did = uuid.UUID(dept_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid department ID")
    
    db_dept = db.query(Department).filter(Department.id == did).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    if dept.name is not None:
        db_dept.name = dept.name
    if dept.allowed_pages is not None:
        db_dept.description = json.dumps(dept.allowed_pages)
    
    db.commit()
    return {"id": str(db_dept.id), "message": "Department updated"}

@departments_router.delete("/{dept_id}")
def delete_department(dept_id: str, db: Session = Depends(get_db)):
    """Delete a department"""
    try:
        did = uuid.UUID(dept_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid department ID")
    
    db_dept = db.query(Department).filter(Department.id == did).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Clear department from users first
    db.query(AppUser).filter(AppUser.department_id == did).update({"department_id": None})
    db.delete(db_dept)
    db.commit()
    
    return {"message": "Department deleted"}

# ============== Seed Default Data ==============

def seed_default_roles(db: Session):
    """Seed default roles if not exist"""
    import json
    
    default_roles = [
        {
            "code": "super_admin",
            "name": "Super Admin",
            "pages": ["dashboard", "orders", "returns", "products", "bundles", "stock", 
                      "outbound", "packing", "promotions", "finance", "invoice", "settings", "admin"]
        },
        {
            "code": "manager",
            "name": "Manager",
            "pages": ["dashboard", "orders", "returns", "products", "stock", "finance"]
        },
        {
            "code": "packer",
            "name": "Packer",
            "pages": ["packing", "orders"]
        },
        {
            "code": "viewer",
            "name": "Viewer",
            "pages": ["dashboard"]
        }
    ]
    
    for role_data in default_roles:
        existing = db.query(Role).filter(Role.code == role_data["code"]).first()
        if not existing:
            role = Role(
                id=uuid.uuid4(),
                code=role_data["code"],
                name=role_data["name"],
                description=json.dumps(role_data["pages"])
            )
            db.add(role)
    
    # Create default admin user if not exists
    admin_exists = db.query(AppUser).filter(AppUser.username == "admin").first()
    if not admin_exists:
        admin_user = AppUser(
            id=uuid.uuid4(),
            username="admin",
            email="admin@weorder.com",
            full_name="System Administrator",
            is_active=True,
            hashed_password="admin123"  # In production, hash this
        )
        db.add(admin_user)
        db.flush()
        
        # Assign super_admin role
        super_admin = db.query(Role).filter(Role.code == "super_admin").first()
        if super_admin:
            user_role = UserRole(user_id=admin_user.id, role_id=super_admin.id)
            db.add(user_role)
    
    db.commit()
