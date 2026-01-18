"""
Authentication API - Login, JWT Token, Password Management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
import json

from app.core import get_db, settings
from app.models import AppUser, Role, UserRole, Department

router = APIRouter(prefix="/auth", tags=["auth"])

# ============== Configuration ==============

SECRET_KEY = getattr(settings, 'SECRET_KEY', 'weorder-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ============== Schemas ==============

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserInfo(BaseModel):
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    roles: List[dict]
    department: Optional[dict]
    allowed_pages: List[str]


# ============== Helper Functions ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_allowed_pages(user: AppUser, db: Session) -> List[str]:
    """
    Get union of allowed pages from Roles and Department
    """
    allowed_pages = set()
    
    # Get from Roles
    for user_role in user.user_roles:
        role = user_role.role
        if role and role.description:
            try:
                pages = json.loads(role.description)
                if isinstance(pages, list):
                    allowed_pages.update(pages)
            except:
                pass
    
    # Get from Department
    if user.department and user.department.description:
        try:
            pages = json.loads(user.department.description)
            if isinstance(pages, list):
                allowed_pages.update(pages)
        except:
            pass
    
    return list(allowed_pages)


def authenticate_user(db: Session, username: str, password: str) -> Optional[AppUser]:
    """Authenticate user by username and password"""
    user = db.query(AppUser).filter(AppUser.username == username).first()
    if not user:
        return None
    if not user.hashed_password:
        # User has no password set - allow login with empty password for initial setup
        if password == "" or password == username:
            return user
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[AppUser]:
    """Get current user from JWT token"""
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    return user


async def get_current_active_user(
    current_user: Optional[AppUser] = Depends(get_current_user)
) -> AppUser:
    """Require authenticated and active user"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    return current_user


# ============== API Endpoints ==============

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password, returns JWT token
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="บัญชีถูกระงับการใช้งาน"
        )
    
    # Get allowed pages
    allowed_pages = get_user_allowed_pages(user, db)
    
    # Create token payload
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "allowed_pages": allowed_pages,
        },
        expires_delta=access_token_expires
    )
    
    # Build user info
    roles = [{"id": str(ur.role.id), "code": ur.role.code, "name": ur.role.name} 
             for ur in user.user_roles if ur.role]
    
    department = None
    if user.department:
        department = {
            "id": str(user.department.id),
            "code": user.department.code,
            "name": user.department.name
        }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": roles,
            "department": department,
            "allowed_pages": allowed_pages,
        }
    }


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: AppUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user info"""
    allowed_pages = get_user_allowed_pages(current_user, db)
    
    roles = [{"id": str(ur.role.id), "code": ur.role.code, "name": ur.role.name} 
             for ur in current_user.user_roles if ur.role]
    
    department = None
    if current_user.department:
        department = {
            "id": str(current_user.department.id),
            "code": current_user.department.code,
            "name": current_user.department.name
        }
    
    return UserInfo(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=roles,
        department=department,
        allowed_pages=allowed_pages,
    )


@router.post("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: AppUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password for current user"""
    # Verify current password (or allow if no password set)
    if current_user.hashed_password:
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="รหัสผ่านปัจจุบันไม่ถูกต้อง"
            )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "เปลี่ยนรหัสผ่านสำเร็จ"}


# Export password hash function for use in users.py
__all__ = ["router", "get_password_hash", "get_current_user", "get_current_active_user"]
