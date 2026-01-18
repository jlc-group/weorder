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

# ============== SSO Configuration ==============
# These settings should be configured in .env for production
SSO_ENABLED = getattr(settings, 'SSO_ENABLED', True)
SSO_JWT_SECRET = getattr(settings, 'SSO_JWT_SECRET', None)  # Public key from SSO server
SSO_JWT_ALGORITHM = getattr(settings, 'SSO_JWT_ALGORITHM', 'HS256')  # RS256 for production
SSO_ISSUER = getattr(settings, 'SSO_ISSUER', 'https://sso.jlcgroup.co')
SSO_LOGIN_URL = getattr(settings, 'SSO_LOGIN_URL', 'https://sso.jlcgroup.co/login')

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


class SSOLoginRequest(BaseModel):
    """Request body for SSO login"""
    token: str  # JWT token from external SSO server


class SSOTokenClaims(BaseModel):
    """Expected claims in SSO JWT token"""
    sub: str  # User ID from SSO
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None  # Full name
    roles: Optional[List[str]] = []  # Role codes: ["admin", "manager"]
    pages: Optional[List[str]] = []  # Allowed pages: ["dashboard", "orders"]
    iss: Optional[str] = None  # Issuer
    exp: Optional[int] = None  # Expiry timestamp

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


# ============== SSO Authentication ==============

def verify_sso_token(token: str) -> Optional[dict]:
    """
    Verify JWT token from external SSO server.
    Returns decoded claims if valid, None if invalid.
    
    For production:
    - Use RS256 with SSO server's public key
    - Verify issuer (iss) matches SSO_ISSUER
    - Check token expiry (exp)
    """
    try:
        # Use SSO secret/public key if configured, otherwise use our secret for testing
        secret = SSO_JWT_SECRET if SSO_JWT_SECRET else SECRET_KEY
        algorithm = SSO_JWT_ALGORITHM if SSO_JWT_SECRET else ALGORITHM
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={
                "verify_iss": bool(SSO_ISSUER),
                "require": ["sub"]
            },
            issuer=SSO_ISSUER if SSO_ISSUER else None
        )
        return payload
    except JWTError as e:
        print(f"SSO token verification failed: {e}")
        return None


def get_or_create_sso_user(db: Session, claims: dict) -> AppUser:
    """
    Get user by SSO ID or create new user from SSO claims.
    
    Expected claims:
    - sub: unique user ID from SSO
    - username: login username
    - email: user email
    - name: full name
    - roles: list of role codes
    - pages: list of allowed page keys
    """
    import uuid as uuid_lib
    
    sso_id = claims.get("sub")
    username = claims.get("username") or claims.get("preferred_username") or sso_id
    email = claims.get("email")
    full_name = claims.get("name") or claims.get("full_name")
    
    # Try to find existing user by username
    user = db.query(AppUser).filter(AppUser.username == username).first()
    
    if not user:
        # Create new user from SSO claims
        user = AppUser(
            id=uuid_lib.uuid4(),
            username=username,
            email=email,
            full_name=full_name,
            is_active=True,
            hashed_password=None  # SSO users don't have local password
        )
        db.add(user)
        db.flush()
        
        # Try to assign roles from claims
        role_codes = claims.get("roles", [])
        for role_code in role_codes:
            role = db.query(Role).filter(Role.code == role_code).first()
            if role:
                from app.models import UserRole
                user_role = UserRole(user_id=user.id, role_id=role.id)
                db.add(user_role)
        
        db.commit()
        db.refresh(user)
    else:
        # Update existing user info
        if email and user.email != email:
            user.email = email
        if full_name and user.full_name != full_name:
            user.full_name = full_name
        db.commit()
    
    return user


@router.post("/sso", response_model=Token)
async def sso_login(
    request: SSOLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login using JWT token from JLC Group SSO Server.
    
    Flow:
    1. User logs in at SSO server
    2. SSO server redirects to /auth/callback?token=<JWT>
    3. Frontend sends token to this endpoint
    4. We verify token, create/update user, and return WeOrder session
    
    Expected JWT Claims from SSO:
    - sub: Unique user ID
    - username: Login username
    - email: User email (optional)
    - name: Full name (optional)
    - roles: ["super_admin", "manager", ...] (optional)
    - pages: ["dashboard", "orders", ...] (optional)
    """
    if not SSO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SSO login is not enabled"
        )
    
    # Verify SSO token
    claims = verify_sso_token(request.token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSO token"
        )
    
    # Get or create user from SSO claims
    user = get_or_create_sso_user(db, claims)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="บัญชีถูกระงับการใช้งาน"
        )
    
    # Determine allowed pages (from SSO claims or from local DB roles/dept)
    sso_pages = claims.get("pages", [])
    if sso_pages:
        allowed_pages = sso_pages
    else:
        allowed_pages = get_user_allowed_pages(user, db)
    
    # Create WeOrder session token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "allowed_pages": allowed_pages,
            "sso": True,  # Mark as SSO login
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Build user info response
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


@router.get("/sso/config")
async def get_sso_config():
    """
    Get SSO configuration for frontend.
    Returns SSO login URL and enabled status.
    """
    return {
        "enabled": SSO_ENABLED,
        "login_url": SSO_LOGIN_URL,
        "issuer": SSO_ISSUER
    }


# Export password hash function for use in users.py
__all__ = ["router", "get_password_hash", "get_current_user", "get_current_active_user"]

