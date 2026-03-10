"""
auth.py — ระบบ Authentication & Authorization
==============================================
รองรับ 2 ประเภทผู้ใช้:
  - Staff: FrontDesk, Finance, Manager (username + password)
  - Guest: ลงทะเบียนในระบบ (email + password)

ใช้ JWT Token สำหรับ stateless auth
"""

from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ══════════════════════════════════════════════════════════════
#  Config
# ══════════════════════════════════════════════════════════════

SECRET_KEY    = "hotel-secret-key-change-in-production-2026"
ALGORITHM     = "HS256"
TOKEN_EXPIRE_MINUTES = 480  # 8 ชั่วโมง

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ══════════════════════════════════════════════════════════════
#  Roles
# ══════════════════════════════════════════════════════════════

class Role(str, Enum):
    GUEST       = "guest"
    FRONT_DESK  = "front_desk"
    FINANCE     = "finance"
    MANAGER     = "manager"


# ══════════════════════════════════════════════════════════════
#  สิทธิ์ของแต่ละ Role
# ══════════════════════════════════════════════════════════════

ROLE_PERMISSIONS = {
    Role.GUEST: [
        "reservation:create",
        "reservation:read_own",
        "reservation:cancel_own",
        "room:search",
        "invoice:read_own",
        "guest:read_own",
    ],
    Role.FRONT_DESK: [
        "reservation:create",
        "reservation:read",
        "reservation:confirm",
        "reservation:checkin",
        "reservation:checkout",
        "reservation:cancel",
        "reservation:noshow",
        "room:read",
        "room:search",
        "room:cleaning",
        "guest:read",
        "guest:create",
        "invoice:read",
        "auditlog:read",
    ],
    Role.FINANCE: [
        "reservation:read",
        "reservation:confirm",
        "payment:process",
        "invoice:read",
        "invoice:manage",
        "report:revenue",
        "report:cancellation",
        "auditlog:read",
        "guest:read",
        "room:read",
    ],
    Role.MANAGER: [
        # Manager เข้าถึงได้ทุกอย่าง
        "reservation:create",
        "reservation:read",
        "reservation:confirm",
        "reservation:checkin",
        "reservation:checkout",
        "reservation:cancel",
        "reservation:noshow",
        "room:read",
        "room:search",
        "room:cleaning",
        "room:manage",
        "guest:read",
        "guest:create",
        "invoice:read",
        "invoice:manage",
        "payment:process",
        "report:occupancy",
        "report:revenue",
        "report:cancellation",
        "auditlog:read",
        "staff:manage",
    ],
}


# ══════════════════════════════════════════════════════════════
#  User Database (เก็บใน memory — เปลี่ยนเป็น DB ได้ภายหลัง)
# ══════════════════════════════════════════════════════════════

class UserInDB(BaseModel):
    username:      str
    hashed_password: str
    role:          Role
    full_name:     str
    email:         str
    is_active:     bool = True
    guest_id:      Optional[str] = None  # สำหรับ Guest เท่านั้น


def _hash(password: str) -> str:
    return pwd_context.hash(password)


# Staff accounts (username + password)
# Guest accounts สร้างอัตโนมัติตอน register_guest
STAFF_DB: dict[str, UserInDB] = {
    "frontdesk01": UserInDB(
        username="frontdesk01",
        hashed_password=_hash("front1234"),
        role=Role.FRONT_DESK,
        full_name="สมชาย ฟร้อนท์เดสก์",
        email="frontdesk01@hotel.com",
    ),
    "frontdesk02": UserInDB(
        username="frontdesk02",
        hashed_password=_hash("front5678"),
        role=Role.FRONT_DESK,
        full_name="สมหญิง ฟร้อนท์เดสก์",
        email="frontdesk02@hotel.com",
    ),
    "finance01": UserInDB(
        username="finance01",
        hashed_password=_hash("finance1234"),
        role=Role.FINANCE,
        full_name="วิภา การเงิน",
        email="finance01@hotel.com",
    ),
    "manager01": UserInDB(
        username="manager01",
        hashed_password=_hash("manager1234"),
        role=Role.MANAGER,
        full_name="ประยุทธ ผู้จัดการ",
        email="manager01@hotel.com",
    ),
}

# Guest accounts — key คือ email
GUEST_DB: dict[str, UserInDB] = {}


# ══════════════════════════════════════════════════════════════
#  Helper Functions
# ══════════════════════════════════════════════════════════════

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_user(username_or_email: str) -> Optional[UserInDB]:
    """ค้นหา user จาก staff DB ก่อน ถ้าไม่เจอค้นใน guest DB"""
    if username_or_email in STAFF_DB:
        return STAFF_DB[username_or_email]
    if username_or_email in GUEST_DB:
        return GUEST_DB[username_or_email]
    return None


def authenticate_user(username_or_email: str, password: str) -> Optional[UserInDB]:
    user = get_user(username_or_email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def register_guest_account(guest_id: str, name: str, email: str, password: str) -> UserInDB:
    """สร้าง account สำหรับแขกใหม่"""
    user = UserInDB(
        username=email,
        hashed_password=_hash(password),
        role=Role.GUEST,
        full_name=name,
        email=email,
        guest_id=guest_id,
    )
    GUEST_DB[email] = user
    return user


# ══════════════════════════════════════════════════════════════
#  FastAPI Dependencies
# ══════════════════════════════════════════════════════════════

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token ไม่ถูกต้องหรือหมดอายุ กรุณา Login ใหม่",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_permission(permission: str):
    """
    Dependency factory — ใช้ใน endpoint แบบนี้:
        current_user = Depends(require_permission("reservation:create"))
    """
    async def checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        allowed = ROLE_PERMISSIONS.get(current_user.role, [])
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' ไม่มีสิทธิ์ใช้งาน '{permission}'",
            )
        return current_user
    return checker


def require_roles(*roles: Role):
    """
    Dependency factory — กำหนดได้หลาย role:
        current_user = Depends(require_roles(Role.MANAGER, Role.FINANCE))
    """
    async def checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"เฉพาะ {[r.value for r in roles]} เท่านั้น",
            )
        return current_user
    return checker
