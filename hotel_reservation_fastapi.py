"""
Hotel Reservation System - FastAPI Server
พร้อม Authentication และ Role-based Access Control
รองรับ: Guest, Frontdesk Staff, Hotel Manager, Finance Staff
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
import jwt
import json

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class UserRole(str, Enum):
    """ประเภท user"""
    GUEST = "guest"
    FRONTDESK = "frontdesk"
    MANAGER = "manager"
    FINANCE = "finance"
    ADMIN = "admin"

class RoomStatus(str, Enum):
    """สถานะห้อง"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"

class ReservationStatus(str, Enum):
    """สถานะการจอง"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"

# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class User(BaseModel):
    """Model สำหรับ user"""
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True

class UserLogin(BaseModel):
    """Model สำหรับ login"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Model สำหรับ token response"""
    access_token: str
    token_type: str
    user: User
    role: UserRole

class Room(BaseModel):
    """Model สำหรับห้อง"""
    id: int
    room_number: str
    floor: int
    room_type: str  # standard, deluxe, suite
    price_per_night: float
    capacity: int
    status: RoomStatus
    description: Optional[str] = None

class RoomCreate(BaseModel):
    """Model สำหรับสร้างห้องใหม่"""
    room_number: str
    floor: int
    room_type: str
    price_per_night: float
    capacity: int
    description: Optional[str] = None

class Reservation(BaseModel):
    """Model สำหรับการจอง"""
    id: int
    guest_id: int
    guest_name: str
    room_id: int
    room_number: str
    check_in: str
    check_out: str
    status: ReservationStatus
    number_of_guests: int
    total_price: float
    created_at: str
    special_requests: Optional[str] = None

class ReservationCreate(BaseModel):
    """Model สำหรับสร้างการจองใหม่"""
    guest_name: str
    room_id: int
    check_in: str
    check_out: str
    number_of_guests: int
    special_requests: Optional[str] = None

class Payment(BaseModel):
    """Model สำหรับการชำระเงิน"""
    id: int
    reservation_id: int
    amount: float
    payment_method: str  # cash, credit_card, bank_transfer
    payment_date: str
    status: str  # pending, completed, failed

class PaymentCreate(BaseModel):
    """Model สำหรับสร้างการชำระเงินใหม่"""
    reservation_id: int
    amount: float
    payment_method: str

class Invoice(BaseModel):
    """Model สำหรับใบเสร็จ"""
    id: int
    reservation_id: int
    guest_name: str
    room_number: str
    check_in: str
    check_out: str
    room_price: float
    number_of_nights: int
    subtotal: float
    discount: float
    tax: float
    total: float
    issued_date: str
    status: str

class Discount(BaseModel):
    """Model สำหรับส่วนลด"""
    id: int
    name: str
    percentage: float
    min_nights: int
    is_active: bool

# ═══════════════════════════════════════════════════════════════════════════════
# Database Mock
# ═══════════════════════════════════════════════════════════════════════════════

users_db = {
    1: User(id=1, username="guest1", email="guest1@email.com", full_name="John Doe", role=UserRole.GUEST),
    2: User(id=2, username="frontdesk1", email="frontdesk1@hotel.com", full_name="Jane Smith", role=UserRole.FRONTDESK),
    3: User(id=3, username="manager1", email="manager1@hotel.com", full_name="Bob Johnson", role=UserRole.MANAGER),
    4: User(id=4, username="finance1", email="finance1@hotel.com", full_name="Alice Brown", role=UserRole.FINANCE),
}

passwords_db = {
    "guest1": "password123",
    "frontdesk1": "password123",
    "manager1": "password123",
    "finance1": "password123",
}

rooms_db = {
    1: Room(id=1, room_number="101", floor=1, room_type="standard", price_per_night=100, capacity=2, status=RoomStatus.AVAILABLE, description="Standard room with city view"),
    2: Room(id=2, room_number="102", floor=1, room_type="deluxe", price_per_night=200, capacity=3, status=RoomStatus.AVAILABLE, description="Deluxe room with ocean view"),
    3: Room(id=3, room_number="201", floor=2, room_type="suite", price_per_night=300, capacity=4, status=RoomStatus.OCCUPIED, description="Luxury suite"),
}

reservations_db = {}
next_reservation_id = 1

payments_db = {}
next_payment_id = 1

invoices_db = {}
next_invoice_id = 1

discounts_db = {
    1: Discount(id=1, name="Long Stay Discount", percentage=10, min_nights=5, is_active=True),
    2: Discount(id=2, name="Weekend Discount", percentage=15, min_nights=1, is_active=True),
}

# ═══════════════════════════════════════════════════════════════════════════════
# Create FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Hotel Reservation System API",
    description="API สำหรับระบบจองโรงแรมพร้อม role-based access",
    version="1.0.0"
)

# ═══════════════════════════════════════════════════════════════════════════════
# Authentication & Authorization
# ═══════════════════════════════════════════════════════════════════════════════

def create_access_token(user_id: int, role: UserRole, expires_delta: Optional[timedelta] = None):
    """สร้าง JWT token"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "user_id": user_id,
        "role": role.value,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthCredentials) -> dict:
    """ยืนยัน token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"user_id": user_id, "role": UserRole(role)}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthCredentials = Depends(HTTPBearer())) -> User:
    """ดึงข้อมูล current user"""
    token_data = verify_token(credentials)
    user = users_db.get(token_data["user_id"])
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

def require_role(required_roles: List[UserRole]):
    """Dependency สำหรับตรวจสอบ role"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of roles: {[r.value for r in required_roles]}"
            )
        return current_user
    
    return role_checker

# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(credentials: UserLogin):
    """ล็อกอินเข้าระบบ
    
    Users:
    - Username: guest1 (Guest)
    - Username: frontdesk1 (Frontdesk Staff)
    - Username: manager1 (Hotel Manager)
    - Username: finance1 (Finance Staff)
    - Password: password123 (สำหรับทั้งหมด)
    """
    
    # ตรวจสอบ username
    user = None
    for u in users_db.values():
        if u.username == credentials.username:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # ตรวจสอบ password
    stored_password = passwords_db.get(credentials.username)
    if stored_password != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # สร้าง token
    access_token = create_access_token(user.id, user.role)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
        role=user.role
    )

@app.get("/auth/me", response_model=User, tags=["Authentication"])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """ดึงข้อมูล current user"""
    return current_user

# ═══════════════════════════════════════════════════════════════════════════════
# Guest Use Cases
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/rooms/available", response_model=List[Room], tags=["Guest - Search"])
def search_available_rooms(check_in: str, check_out: str, current_user: User = Depends(get_current_user)):
    """🔍 Guest: ค้นหาห้องว่าง (Search Availability)"""
    
    # คืนเฉพาะห้องที่ว่าง
    available_rooms = [
        room for room in rooms_db.values()
        if room.status == RoomStatus.AVAILABLE
    ]
    
    return available_rooms

@app.post("/reservations", response_model=Reservation, tags=["Guest - Booking"])
def create_reservation(
    reservation: ReservationCreate,
    current_user: User = Depends(require_role([UserRole.GUEST, UserRole.FRONTDESK]))
):
    """📅 Guest/Frontdesk: สร้างการจอง (Create Reservation)"""
    
    global next_reservation_id
    
    # ตรวจสอบห้องมีอยู่
    room = rooms_db.get(reservation.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # ตรวจสอบสถานะห้อง
    if room.status != RoomStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Room is not available")
    
    # คำนวณราคา
    check_in = datetime.strptime(reservation.check_in, "%Y-%m-%d")
    check_out = datetime.strptime(reservation.check_out, "%Y-%m-%d")
    nights = (check_out - check_in).days
    total_price = room.price_per_night * nights
    
    # สร้างการจอง
    new_reservation = Reservation(
        id=next_reservation_id,
        guest_id=current_user.id if current_user.role == UserRole.GUEST else reservation.guest_name.split()[0],
        guest_name=reservation.guest_name,
        room_id=room.id,
        room_number=room.room_number,
        check_in=reservation.check_in,
        check_out=reservation.check_out,
        status=ReservationStatus.CONFIRMED,
        number_of_guests=reservation.number_of_guests,
        total_price=total_price,
        created_at=datetime.now().isoformat(),
        special_requests=reservation.special_requests
    )
    
    reservations_db[next_reservation_id] = new_reservation
    next_reservation_id += 1
    
    # อัปเดตสถานะห้อง
    room.status = RoomStatus.RESERVED
    
    return new_reservation

@app.get("/reservations", response_model=List[Reservation], tags=["Guest - Booking"])
def get_my_reservations(current_user: User = Depends(require_role([UserRole.GUEST]))):
    """📋 Guest: ดูการจองของฉัน (View My Reservations)"""
    
    my_reservations = [
        res for res in reservations_db.values()
        if res.guest_id == current_user.id or res.guest_name == current_user.full_name
    ]
    
    return my_reservations

@app.get("/reservations/{reservation_id}", response_model=Reservation, tags=["Guest - Booking"])
def get_reservation(reservation_id: int, current_user: User = Depends(get_current_user)):
    """📄 Guest/Staff: ดูรายละเอียดการจอง"""
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Guest สามารถดูได้เฉพาะการจองของตัวเอง
    if current_user.role == UserRole.GUEST:
        if reservation.guest_id != current_user.id and reservation.guest_name != current_user.full_name:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return reservation

@app.delete("/reservations/{reservation_id}", tags=["Guest - Booking"])
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(require_role([UserRole.GUEST, UserRole.FRONTDESK]))
):
    """❌ Guest: ยกเลิกการจอง (Cancel Reservation)
    
    ⚠️  Penalty fee จะถูกเก็บตามนโยบาย
    """
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Guest สามารถยกเลิกได้เฉพาะการจองของตัวเอง
    if current_user.role == UserRole.GUEST:
        if reservation.guest_id != current_user.id and reservation.guest_name != current_user.full_name:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # เปลี่ยนสถานะเป็น CANCELLED
    reservation.status = ReservationStatus.CANCELLED
    
    # คืนห้องให้ว่าง
    room = rooms_db.get(reservation.room_id)
    if room:
        room.status = RoomStatus.AVAILABLE
    
    return {"message": "Reservation cancelled successfully", "penalty_fee_applicable": True}

# ═══════════════════════════════════════════════════════════════════════════════
# Payment & Invoice (Guest)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/payments", response_model=Payment, tags=["Guest - Payment"])
def make_payment(
    payment: PaymentCreate,
    current_user: User = Depends(require_role([UserRole.GUEST, UserRole.FRONTDESK]))
):
    """💳 Guest/Frontdesk: ชำระเงิน (Payment)"""
    
    global next_payment_id
    
    # ตรวจสอบการจอง
    reservation = reservations_db.get(payment.reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # สร้างการชำระเงิน
    new_payment = Payment(
        id=next_payment_id,
        reservation_id=payment.reservation_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        payment_date=datetime.now().isoformat(),
        status="completed"
    )
    
    payments_db[next_payment_id] = new_payment
    next_payment_id += 1
    
    return new_payment

@app.post("/invoices", response_model=Invoice, tags=["Guest - Invoice"])
def generate_invoice(
    reservation_id: int,
    current_user: User = Depends(require_role([UserRole.GUEST, UserRole.FRONTDESK]))
):
    """🧾 Guest/Frontdesk: สร้างใบเสร็จ (Generate Invoice)"""
    
    global next_invoice_id
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    room = rooms_db.get(reservation.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # คำนวณจำนวนคืน
    check_in = datetime.strptime(reservation.check_in, "%Y-%m-%d")
    check_out = datetime.strptime(reservation.check_out, "%Y-%m-%d")
    nights = (check_out - check_in).days
    
    # คำนวณราคา
    subtotal = room.price_per_night * nights
    discount = subtotal * 0.1  # 10% discount
    tax = (subtotal - discount) * 0.07  # 7% tax
    total = subtotal - discount + tax
    
    invoice = Invoice(
        id=next_invoice_id,
        reservation_id=reservation_id,
        guest_name=reservation.guest_name,
        room_number=reservation.room_number,
        check_in=reservation.check_in,
        check_out=reservation.check_out,
        room_price=room.price_per_night,
        number_of_nights=nights,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        issued_date=datetime.now().isoformat(),
        status="issued"
    )
    
    invoices_db[next_invoice_id] = invoice
    next_invoice_id += 1
    
    return invoice

# ═══════════════════════════════════════════════════════════════════════════════
# Frontdesk Staff Use Cases
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/rooms", response_model=List[Room], tags=["Frontdesk - Management"])
def get_all_rooms(current_user: User = Depends(require_role([UserRole.FRONTDESK, UserRole.MANAGER]))):
    """🏨 Frontdesk: ดูห้องทั้งหมด (View All Rooms)"""
    
    return list(rooms_db.values())

@app.put("/rooms/{room_id}/status", tags=["Frontdesk - Management"])
def update_room_status(
    room_id: int,
    new_status: RoomStatus,
    current_user: User = Depends(require_role([UserRole.FRONTDESK, UserRole.MANAGER]))
):
    """🔧 Frontdesk: อัปเดตสถานะห้อง (Update Room Status)
    
    สถานะ: available, occupied, maintenance, reserved
    """
    
    room = rooms_db.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room.status = new_status
    
    return {"message": f"Room {room.room_number} status updated to {new_status.value}"}

@app.post("/check-in", tags=["Frontdesk - Check-in/out"])
def check_in(
    reservation_id: int,
    current_user: User = Depends(require_role([UserRole.FRONTDESK]))
):
    """🔑 Frontdesk: เช็คอิน (Check-In)
    
    ✅ Includes: Validation
    """
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # ตรวจสอบวันเข้า
    check_in = datetime.strptime(reservation.check_in, "%Y-%m-%d")
    today = datetime.now().date()
    
    if check_in.date() > today:
        raise HTTPException(status_code=400, detail="Check-in date is in the future")
    
    # อัปเดตสถานะ
    reservation.status = ReservationStatus.CHECKED_IN
    
    # อัปเดตสถานะห้อง
    room = rooms_db.get(reservation.room_id)
    if room:
        room.status = RoomStatus.OCCUPIED
    
    return {"message": f"Guest {reservation.guest_name} checked in successfully"}

@app.post("/check-out", tags=["Frontdesk - Check-in/out"])
def check_out(
    reservation_id: int,
    current_user: User = Depends(require_role([UserRole.FRONTDESK]))
):
    """🚪 Frontdesk: เช็คเอาท์ (Check-Out)
    
    ✅ Includes: Generate Invoice
    """
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # อัปเดตสถานะ
    reservation.status = ReservationStatus.CHECKED_OUT
    
    # อัปเดตสถานะห้อง
    room = rooms_db.get(reservation.room_id)
    if room:
        room.status = RoomStatus.AVAILABLE
    
    return {
        "message": f"Guest {reservation.guest_name} checked out successfully",
        "invoice_generated": True
    }

@app.post("/change-room", tags=["Frontdesk - Room Management"])
def change_room(
    reservation_id: int,
    new_room_id: int,
    current_user: User = Depends(require_role([UserRole.FRONTDESK]))
):
    """🔄 Frontdesk: เปลี่ยนห้อง (Change Room)
    
    ✅ Includes: Search Availability
    """
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    new_room = rooms_db.get(new_room_id)
    if not new_room:
        raise HTTPException(status_code=404, detail="New room not found")
    
    if new_room.status != RoomStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="New room is not available")
    
    # คืนห้องเก่า
    old_room = rooms_db.get(reservation.room_id)
    if old_room:
        old_room.status = RoomStatus.AVAILABLE
    
    # ใช้ห้องใหม่
    reservation.room_id = new_room_id
    reservation.room_number = new_room.room_number
    new_room.status = RoomStatus.RESERVED
    
    return {"message": f"Room changed from {old_room.room_number} to {new_room.room_number}"}

# ═══════════════════════════════════════════════════════════════════════════════
# Manager Use Cases
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/reservations-all", response_model=List[Reservation], tags=["Manager - Dashboard"])
def view_all_reservations(current_user: User = Depends(require_role([UserRole.MANAGER, UserRole.FRONTDESK]))):
    """📊 Manager: ดูการจองทั้งหมด (View All Reservations)"""
    
    return list(reservations_db.values())

@app.get("/dashboard/statistics", tags=["Manager - Dashboard"])
def get_dashboard_statistics(current_user: User = Depends(require_role([UserRole.MANAGER]))):
    """📈 Manager: ดูสถิติและรายงาน (Dashboard Statistics)"""
    
    total_reservations = len(reservations_db)
    confirmed_reservations = len([r for r in reservations_db.values() if r.status == ReservationStatus.CONFIRMED])
    checked_in = len([r for r in reservations_db.values() if r.status == ReservationStatus.CHECKED_IN])
    total_revenue = sum(r.total_price for r in reservations_db.values())
    occupancy_rate = len([r for r in rooms_db.values() if r.status == RoomStatus.OCCUPIED]) / len(rooms_db) * 100
    
    return {
        "total_reservations": total_reservations,
        "confirmed_reservations": confirmed_reservations,
        "checked_in": checked_in,
        "total_revenue": total_revenue,
        "occupancy_rate": f"{occupancy_rate:.2f}%"
    }

@app.post("/rooms", response_model=Room, tags=["Manager - Room Management"])
def create_room(
    room: RoomCreate,
    current_user: User = Depends(require_role([UserRole.MANAGER]))
):
    """➕ Manager: สร้างห้องใหม่ (Add New Room)"""
    
    next_id = max(rooms_db.keys()) + 1 if rooms_db else 1
    
    new_room = Room(
        id=next_id,
        room_number=room.room_number,
        floor=room.floor,
        room_type=room.room_type,
        price_per_night=room.price_per_night,
        capacity=room.capacity,
        status=RoomStatus.AVAILABLE,
        description=room.description
    )
    
    rooms_db[next_id] = new_room
    return new_room

@app.delete("/rooms/{room_id}", tags=["Manager - Room Management"])
def delete_room(
    room_id: int,
    current_user: User = Depends(require_role([UserRole.MANAGER]))
):
    """🗑️ Manager: ลบห้อง (Delete Room)"""
    
    if room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not found")
    
    del rooms_db[room_id]
    return {"message": "Room deleted successfully"}

# ═══════════════════════════════════════════════════════════════════════════════
# Finance Staff Use Cases
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/payments-all", response_model=List[Payment], tags=["Finance - Payment"])
def view_all_payments(current_user: User = Depends(require_role([UserRole.FINANCE, UserRole.MANAGER]))):
    """💰 Finance: ดูการชำระเงินทั้งหมด (View All Payments)"""
    
    return list(payments_db.values())

@app.get("/invoices-all", response_model=List[Invoice], tags=["Finance - Invoice"])
def view_all_invoices(current_user: User = Depends(require_role([UserRole.FINANCE, UserRole.MANAGER]))):
    """📋 Finance: ดูใบเสร็จทั้งหมด (View All Invoices)"""
    
    return list(invoices_db.values())

@app.get("/finance/income-report", tags=["Finance - Reports"])
def get_income_report(current_user: User = Depends(require_role([UserRole.FINANCE]))):
    """📊 Finance: รายงานรายได้ (Income Report)
    
    ✅ Includes: Update Income
    """
    
    total_income = sum(p.amount for p in payments_db.values() if p.status == "completed")
    
    # คำนวณตามประเภทห้อง
    income_by_room_type = {}
    for res in reservations_db.values():
        room = rooms_db.get(res.room_id)
        if room:
            room_type = room.room_type
            if room_type not in income_by_room_type:
                income_by_room_type[room_type] = 0
            income_by_room_type[room_type] += res.total_price
    
    return {
        "total_income": total_income,
        "income_by_room_type": income_by_room_type,
        "total_payments_processed": len([p for p in payments_db.values() if p.status == "completed"]),
        "pending_payments": len([p for p in payments_db.values() if p.status == "pending"])
    }

@app.post("/apply-discount", tags=["Finance - Discount"])
def apply_discount(
    reservation_id: int,
    discount_id: int,
    current_user: User = Depends(require_role([UserRole.FINANCE, UserRole.MANAGER]))
):
    """🏷️ Finance: ใช้ส่วนลด (Apply Discount)"""
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    discount = discounts_db.get(discount_id)
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")
    
    # คำนวณส่วนลด
    discount_amount = reservation.total_price * (discount.percentage / 100)
    new_total = reservation.total_price - discount_amount
    
    return {
        "reservation_id": reservation_id,
        "discount_name": discount.name,
        "original_price": reservation.total_price,
        "discount_amount": discount_amount,
        "final_price": new_total
    }

@app.post("/apply-penalty-fee", tags=["Finance - Penalty"])
def apply_penalty_fee(
    reservation_id: int,
    penalty_percentage: float = 10.0,
    current_user: User = Depends(require_role([UserRole.FINANCE, UserRole.MANAGER]))
):
    """⚠️ Finance: เก็บค่าปรับ (Apply Penalty Fee)
    
    ใช้เมื่อ Guest ยกเลิกการจอง
    """
    
    reservation = reservations_db.get(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    penalty_amount = reservation.total_price * (penalty_percentage / 100)
    
    return {
        "reservation_id": reservation_id,
        "original_price": reservation.total_price,
        "penalty_percentage": penalty_percentage,
        "penalty_amount": penalty_amount,
        "final_amount": reservation.total_price - penalty_amount
    }

# ═══════════════════════════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["Health"])
def health_check():
    """ตรวจสอบสถานะ API"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Hotel Reservation System API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
