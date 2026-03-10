"""
Hotel Reservation API — main.py (with Authentication)
=======================================================
เพิ่มระบบ Login แยกตาม Role:
  - Guest    : email + password | จองห้อง / ดูการจองตัวเอง
  - FrontDesk: username + password | เช็คอิน/เอาท์ / จัดการแขก
  - Finance  : username + password | จัดการการเงิน / รายงาน
  - Manager  : username + password | ทุกอย่าง

วิธีรัน:
    pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt]
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Path, Query, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from hotel import (
    Hotel, RoomType, RoomState, BookingChannel, ReservationStatus,
    CardPayment, BankTransferPayment, QRPayment, AuditLog,
)
from auth import (
    UserInDB, Role, authenticate_user, create_access_token,
    get_current_user, require_permission, require_roles,
    register_guest_account, STAFF_DB, GUEST_DB,
)

# ══════════════════════════════════════════════════════════════
#  App
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="🏨 Hotel Reservation API",
    description="""
## ระบบจองโรงแรม — พร้อมระบบ Login

### 👤 ประเภทผู้ใช้งาน

| Role | Username | Password | สิทธิ์ |
|------|----------|----------|--------|
| FrontDesk | `frontdesk01` | `front1234` | เช็คอิน/เอาท์, จัดการแขก |
| FrontDesk | `frontdesk02` | `front5678` | เช็คอิน/เอาท์, จัดการแขก |
| Finance | `finance01` | `finance1234` | การเงิน, รายงาน |
| Manager | `manager01` | `manager1234` | ทุกอย่าง |
| Guest | email | password ที่ตั้งตอนสมัคร | จองห้อง, ดูการจองตัวเอง |

### 🔐 วิธี Login
1. เรียก `POST /auth/login` ด้วย username/email + password
2. นำ `access_token` ที่ได้ไปใส่ใน **Authorize** (ปุ่มบนขวา)
3. พิมพ์ `Bearer <token>` หรือแค่ `<token>` ก็ได้

### ℹ️ Permissions (สรุป)
- Manager: มีสิทธิ์ทุกอย่างในระบบ (สามารถทำทุก action ได้) — ใช้สำหรับผู้ดูแลระบบหรือผู้จัดการโรงแรม
- FrontDesk: จัดการการเช็คอิน/เช็คเอาท์, เปลี่ยนสถานะห้อง, สร้าง/แก้ไขการจองสำหรับแขก
- Finance: จัดการการชำระเงิน, สร้าง/ดูใบแจ้งหนี้, รันรายงานทางการเงิน และใช้ส่วนลด/เก็บค่าปรับ
- Guest: จองห้อง, ชำระเงินของตัวเอง, ดูการจองและข้อมูลส่วนตัว

ตัวอย่าง permission keys ที่ใช้ในระบบ: `reservation:create`, `reservation:confirm`, `reservation:checkin`, `reservation:checkout`, `room:read`, `room:manage`, `report:revenue`, `payment:process`, `auditlog:read`

> หมายเหตุ: Manager ถูกตั้งให้มีทุก permission (can do anything) เพื่อความสะดวกในการทดสอบและสาธิต

### ลำดับการทดสอบ
1. Login ด้วย `frontdesk01`
2. `POST /guests` สร้างแขกพร้อมตั้ง password
3. Login ด้วย email แขก
4. `GET /rooms/search` ค้นหาห้อง
5. `POST /reservations` จองห้อง
6. Login ด้วย `frontdesk01` แล้ว confirm + checkin + checkout
    """,
    version="3.0.0",
)

hotel = Hotel()

# Seed guests
_g1 = hotel.register_guest("ตุลยดา ยอดแก้ว",         "0812345678", "pangpang@email.com",  "ID-111111")
_g2 = hotel.register_guest("ปัญญาวัฒน์ ถาวรพิพัฒเดชน์", "0898765432", "aunaun@email.com",    "ID-222222")
_g3 = hotel.register_guest("ธนโชติ โยธา",             "+1-555-0100", "toytoy@email.com",    "PASSPORT-ABC")

# สร้าง guest accounts สำหรับ seed guests (password เริ่มต้น = guest1234)
register_guest_account(_g1.guest_id, _g1.name, _g1.email, "guest1234")
register_guest_account(_g2.guest_id, _g2.name, _g2.email, "guest1234")
register_guest_account(_g3.guest_id, _g3.name, _g3.email, "guest1234")


# ══════════════════════════════════════════════════════════════
#  Pydantic Schemas
# ══════════════════════════════════════════════════════════════

class PaymentChannelType(str, Enum):
    CARD          = "Card"
    BANK_TRANSFER = "BankTransfer"
    QR            = "QR"


class RegisterGuestRequest(BaseModel):
    name:        str = Field(..., description="ชื่อ-นามสกุล")
    phone:       str = Field(..., description="เบอร์โทร")
    email:       str = Field(..., description="อีเมล (ใช้เป็น username login)")
    id_document: str = Field("", description="เลขบัตรประชาชน/พาสปอร์ต")
    password:    str = Field(..., description="รหัสผ่านสำหรับ login (อย่างน้อย 6 ตัว)")
    model_config = {"json_schema_extra": {"examples": [{
        "name": "สมหญิง ดีมาก", "phone": "0876543210",
        "email": "somying@email.com", "id_document": "ID-333333",
        "password": "mypass123"
    }]}}


class CreateReservationRequest(BaseModel):
    guest_id:         str            = Field(..., description="รหัสผู้เข้าพัก เช่น GST0001")
    room_id:          str            = Field(..., description="รหัสห้อง เช่น RM-0101")
    check_in_date:    datetime       = Field(..., description="วันเช็คอิน")
    check_out_date:   datetime       = Field(..., description="วันเช็คเอาท์")
    channel:          BookingChannel = Field(BookingChannel.WEB)
    extra_bed:        bool           = Field(False)
    corporate_code:   str            = Field("")


class PaymentRequest(BaseModel):
    channel:         PaymentChannelType = Field(...)
    card_number:     str = Field("4111111111111111")
    card_expiry:     str = Field("12/28")
    card_cvv:        str = Field("123")
    bank_name:       str = Field("KBank")
    proof_url:       str = Field("")
    wallet_provider: str = Field("PromptPay")


class CancelRequest(BaseModel):
    actor_id: str = Field("staff_001")


class UpdateRoomStatusRequest(BaseModel):
    new_status: RoomState
    reason:     str = Field("")


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def _make_channel(req: PaymentRequest):
    if req.channel == PaymentChannelType.CARD:
        return CardPayment(req.card_number, req.card_expiry, req.card_cvv)
    elif req.channel == PaymentChannelType.BANK_TRANSFER:
        return BankTransferPayment(req.bank_name, req.proof_url)
    else:
        return QRPayment(req.wallet_provider)


def _raise_if_fail(result: dict):
    if not result.get("success"):
        raise HTTPException(400, detail=result.get("message", "Unknown error"))
    return result


def _assert_own_guest(current_user: UserInDB, guest_id: str):
    """Guest เข้าถึงได้แค่ข้อมูลตัวเอง"""
    if current_user.role == Role.GUEST and current_user.guest_id != guest_id:
        raise HTTPException(403, "Guest สามารถดูข้อมูลตัวเองเท่านั้น")


def _assert_own_reservation(current_user: UserInDB, reservation_id: str):
    """Guest เข้าถึงได้แค่การจองของตัวเอง"""
    if current_user.role == Role.GUEST:
        res = hotel.reservations.get(reservation_id)
        if not res:
            raise HTTPException(404, "Reservation not found")
        if res.guest.guest_id != current_user.guest_id:
            raise HTTPException(403, "Guest สามารถดูการจองตัวเองเท่านั้น")


# ══════════════════════════════════════════════════════════════
#  🔐 Auth Endpoints
# ══════════════════════════════════════════════════════════════

@app.post("/auth/login", tags=["🔐 Auth"], summary="Login — รับ Access Token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login สำหรับทุก role:
    - Staff: ใช้ username + password
    - Guest: ใช้ email + password
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="username/email หรือ password ไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "role":         user.role.value,
        "full_name":    user.full_name,
        "guest_id":     user.guest_id,
        "expires_in":   "8 hours",
    }


@app.get("/auth/me", tags=["🔐 Auth"], summary="ดูข้อมูล User ที่ Login อยู่")
def get_me(current_user: UserInDB = Depends(get_current_user)):
    return {
        "username":  current_user.username,
        "full_name": current_user.full_name,
        "email":     current_user.email,
        "role":      current_user.role.value,
        "guest_id":  current_user.guest_id,
    }


@app.get("/auth/staff-accounts", tags=["🔐 Auth"],
         summary="ดู Staff Accounts ทั้งหมด (Manager เท่านั้น)")
def list_staff_accounts(current_user: UserInDB = Depends(require_roles(Role.MANAGER))):
    return [
        {"username": u.username, "full_name": u.full_name,
         "role": u.role.value, "email": u.email, "is_active": u.is_active}
        for u in STAFF_DB.values()
    ]


# ══════════════════════════════════════════════════════════════
#  👤 Guests
# ══════════════════════════════════════════════════════════════

@app.post("/guests", tags=["👤 Guests"], summary="ลงทะเบียนผู้เข้าพักใหม่", status_code=201)
def register_guest(
    body: RegisterGuestRequest,
    current_user: UserInDB = Depends(require_permission("guest:create")),
):
    if len(body.password) < 6:
        raise HTTPException(400, "Password ต้องมีอย่างน้อย 6 ตัวอักษร")
    if body.email in GUEST_DB:
        raise HTTPException(400, "Email นี้มีบัญชีอยู่แล้ว")

    g = hotel.register_guest(body.name, body.phone, body.email, body.id_document)
    register_guest_account(g.guest_id, g.name, g.email, body.password)

    return {
        "guest_id":         g.guest_id,
        "name":             g.name,
        "email":            g.email,
        "deposit_required": g.required_deposit(),
        "login_email":      g.email,
        "message":          "ลงทะเบียนสำเร็จ — ใช้ email และ password ที่ตั้งไว้ login ได้เลย",
    }


@app.get("/guests", tags=["👤 Guests"], summary="ดูผู้เข้าพักทั้งหมด (Staff เท่านั้น)")
def list_guests(
    current_user: UserInDB = Depends(require_permission("guest:read")),
):
    return [
        {"guest_id": g.guest_id, "name": g.name, "phone": g.phone, "email": g.email,
         "no_show_count": g.recent_no_show_count(), "deposit_required": g.required_deposit()}
        for g in hotel.guests.values()
    ]


@app.get("/guests/{guest_id}", tags=["👤 Guests"], summary="ดูข้อมูลผู้เข้าพัก")
def get_guest(
    guest_id: str = Path(..., examples=["GST0001"]),
    current_user: UserInDB = Depends(get_current_user),
):
    _assert_own_guest(current_user, guest_id)  # Guest ดูได้แค่ตัวเอง
    g = hotel.guests.get(guest_id)
    if not g:
        raise HTTPException(404, "Guest not found")
    return {"guest_id": g.guest_id, "name": g.name, "phone": g.phone, "email": g.email,
            "no_show_count": g.recent_no_show_count(), "deposit_required": g.required_deposit()}


# ══════════════════════════════════════════════════════════════
#  🛏️ Rooms
# ══════════════════════════════════════════════════════════════

@app.get("/rooms", tags=["🛏️ Rooms"], summary="ดูห้องทั้งหมด (Staff เท่านั้น)")
def list_rooms(
    room_type: Optional[RoomType]  = Query(None),
    status:    Optional[RoomState] = Query(None),
    current_user: UserInDB = Depends(require_permission("room:read")),
):
    rooms = list(hotel.rooms.values())
    if room_type: rooms = [r for r in rooms if r.room_type == room_type]
    if status:    rooms = [r for r in rooms if r.room_state == status]
    return [{"room_id": r.resource_id, "floor": r.floor, "room_type": r.room_type.value,
             "bed_type": r.bed_type, "smoking": r.smoking, "status": r.room_state.value,
             "price_per_night": r.price_per_night, "maintenance_note": r.maintenance_note}
            for r in rooms]


@app.get("/rooms/search", tags=["🛏️ Rooms"], summary="ค้นหาห้องว่าง (ทุก Role)")
def search_rooms(
    check_in_date:  datetime        = Query(...),
    check_out_date: datetime        = Query(...),
    room_type:      Optional[RoomType] = Query(None),
    current_user: UserInDB = Depends(require_permission("room:search")),
):
    rooms = hotel.find_available_rooms(room_type, check_in_date, check_out_date) if room_type \
        else [r for rt in RoomType
              for r in hotel.find_available_rooms(rt, check_in_date, check_out_date)]
    nights = (check_out_date.date() - check_in_date.date()).days
    return {
        "available_count": len(rooms),
        "nights": nights,
        "rooms": [{"room_id": r.resource_id, "floor": r.floor,
                   "room_type": r.room_type.value, "price_per_night": r.price_per_night,
                   "subtotal": r.price_per_night * nights} for r in rooms],
    }


@app.patch("/rooms/{room_id}/status", tags=["🛏️ Rooms"],
           summary="เปลี่ยนสถานะห้อง (Manager เท่านั้น)")
def update_room_status(
    room_id: str = Path(..., examples=["RM-0101"]),
    body: UpdateRoomStatusRequest = ...,
    current_user: UserInDB = Depends(require_permission("room:manage")),
):
    room = hotel.rooms.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    room.change_state(body.new_status, actor=current_user.username, reason=body.reason)
    return {"room_id": room_id, "new_status": room.room_state.value}


@app.post("/rooms/{room_id}/cleaning-complete", tags=["🛏️ Rooms"],
          summary="แจ้งทำความสะอาดเสร็จ (FrontDesk/Manager)")
def cleaning_complete(
    room_id:   str = Path(..., examples=["RM-0101"]),
    current_user: UserInDB = Depends(require_permission("room:cleaning")),
):
    return _raise_if_fail(hotel.complete_cleaning(room_id, current_user.username))


# ══════════════════════════════════════════════════════════════
#  📅 Reservations
# ══════════════════════════════════════════════════════════════

@app.post("/reservations", tags=["📅 Reservations"],
          summary="สร้างการจองใหม่ (Guest/FrontDesk/Manager)", status_code=201)
def create_reservation(
    body: CreateReservationRequest,
    current_user: UserInDB = Depends(require_permission("reservation:create")),
):
    # Guest จองได้แค่ในนามตัวเอง
    if current_user.role == Role.GUEST and body.guest_id != current_user.guest_id:
        raise HTTPException(403, "Guest สามารถจองในนามตัวเองเท่านั้น")

    result = hotel.create_reservation(
        guest_id=body.guest_id, room_id=body.room_id,
        check_in=body.check_in_date, check_out=body.check_out_date,
        channel=body.channel, extra_bed=body.extra_bed,
        corporate_code=body.corporate_code,
    )
    return _raise_if_fail(result)


@app.get("/reservations", tags=["📅 Reservations"],
         summary="ดูรายการจองทั้งหมด (Staff เท่านั้น)")
def list_reservations(
    status:     Optional[ReservationStatus] = Query(None),
    guest_name: Optional[str]               = Query(None),
    current_user: UserInDB = Depends(require_permission("reservation:read")),
):
    reservations = list(hotel.reservations.values())
    if status:     reservations = [r for r in reservations if r.status == status]
    if guest_name: reservations = [r for r in reservations
                                    if guest_name.lower() in r.guest.name.lower()]
    return [{
        "reservation_id": r.reservation_id, "guest": r.guest.name,
        "room_id": r.room.resource_id, "room_type": r.room.room_type.value,
        "check_in": r.check_in.strftime("%Y-%m-%d %H:%M"),
        "check_out": r.check_out.strftime("%Y-%m-%d %H:%M"),
        "nights": r.nights, "status": r.status.value, "channel": r.channel.value,
        "extra_bed": r.extra_bed, "discount_type": r.discount.discount_type.value,
        "discount_pct": int(r.discount.rate * 100), "deposit": r.deposit_amount,
    } for r in reservations]


@app.get("/reservations/my", tags=["📅 Reservations"],
         summary="ดูการจองของตัวเอง (Guest)")
def my_reservations(
    current_user: UserInDB = Depends(require_permission("reservation:read_own")),
):
    reservations = [r for r in hotel.reservations.values()
                    if r.guest.guest_id == current_user.guest_id]
    return [{
        "reservation_id": r.reservation_id,
        "room_id": r.room.resource_id, "room_type": r.room.room_type.value,
        "check_in": r.check_in.strftime("%Y-%m-%d %H:%M"),
        "check_out": r.check_out.strftime("%Y-%m-%d %H:%M"),
        "nights": r.nights, "status": r.status.value,
        "extra_bed": r.extra_bed, "deposit": r.deposit_amount,
    } for r in reservations]


@app.get("/reservations/{reservation_id}", tags=["📅 Reservations"],
         summary="ดูรายละเอียดการจอง")
def get_reservation(
    reservation_id: str = Path(...),
    current_user: UserInDB = Depends(get_current_user),
):
    _assert_own_reservation(current_user, reservation_id)
    res = hotel.reservations.get(reservation_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    hours_left = res.hours_until_checkin()
    return {
        "reservation_id": res.reservation_id, "guest": res.guest.name,
        "room_id": res.room.resource_id, "room_type": res.room.room_type.value,
        "check_in": res.check_in.strftime("%Y-%m-%d %H:%M"),
        "check_out": res.check_out.strftime("%Y-%m-%d %H:%M"),
        "nights": res.nights, "status": res.status.value,
        "extra_bed": res.extra_bed, "discount_type": res.discount.discount_type.value,
        "discount_rate_pct": int(res.discount.rate * 100),
        "deposit_amount": res.deposit_amount,
        "hours_until_checkin": round(hours_left, 1),
        "cancellation_policy": {
            "is_free_cancel": hours_left >= 48,
            "penalty_if_cancel": (res.room.price_per_night if hours_left < 48 else 0),
        },
        "invoice": res.invoice.to_dict() if res.invoice else None,
        "history": res.history,
    }


@app.post("/reservations/{reservation_id}/confirm", tags=["📅 Reservations"],
          summary="ยืนยันการจอง + ชำระมัดจำ (FrontDesk/Finance/Manager)")
def confirm_reservation(
    reservation_id: str = Path(...),
    body: PaymentRequest = ...,
    current_user: UserInDB = Depends(require_permission("reservation:confirm")),
):
    return _raise_if_fail(hotel.confirm_reservation(reservation_id, _make_channel(body)))


@app.post("/reservations/{reservation_id}/pay-balance", tags=["📅 Reservations"],
          summary="ชำระยอดที่เหลือ (FrontDesk/Finance/Manager)")
def pay_balance(
    reservation_id: str = Path(...),
    body: PaymentRequest = ...,
    current_user: UserInDB = Depends(require_permission("payment:process")),
):
    return _raise_if_fail(hotel.pay_balance(reservation_id, _make_channel(body)))


@app.post("/reservations/{reservation_id}/cancel", tags=["📅 Reservations"],
          summary="ยกเลิกการจอง")
def cancel_reservation(
    reservation_id: str = Path(...),
    body: CancelRequest = ...,
    current_user: UserInDB = Depends(get_current_user),
):
    # Guest ยกเลิกได้แค่ของตัวเอง / Staff ยกเลิกได้ทุกการจอง
    if current_user.role == Role.GUEST:
        _assert_own_reservation(current_user, reservation_id)
        actor = current_user.guest_id
    else:
        if "reservation:cancel" not in __import__("auth").ROLE_PERMISSIONS.get(current_user.role, []):
            raise HTTPException(403, "ไม่มีสิทธิ์ยกเลิกการจอง")
        actor = current_user.username
    return _raise_if_fail(hotel.cancel_reservation(reservation_id, actor))


@app.post("/reservations/{reservation_id}/checkin", tags=["📅 Reservations"],
          summary="เช็คอิน (FrontDesk/Manager)")
def check_in(
    reservation_id: str = Path(...),
    current_user: UserInDB = Depends(require_permission("reservation:checkin")),
):
    return _raise_if_fail(hotel.check_in(reservation_id, current_user.username))


@app.post("/reservations/{reservation_id}/checkout", tags=["📅 Reservations"],
          summary="เช็คเอาท์ (FrontDesk/Manager)")
def check_out(
    reservation_id: str = Path(...),
    current_user: UserInDB = Depends(require_permission("reservation:checkout")),
):
    return _raise_if_fail(hotel.check_out(reservation_id, current_user.username))


@app.post("/reservations/{reservation_id}/noshow", tags=["📅 Reservations"],
          summary="บันทึก No-show (FrontDesk/Manager)")
def mark_no_show(
    reservation_id: str = Path(...),
    current_user: UserInDB = Depends(require_permission("reservation:noshow")),
):
    return _raise_if_fail(hotel.mark_no_show(reservation_id, current_user.username))


# ══════════════════════════════════════════════════════════════
#  🧾 Invoices
# ══════════════════════════════════════════════════════════════

@app.get("/invoices/{reservation_id}", tags=["🧾 Invoices"],
         summary="ดูใบแจ้งหนี้")
def get_invoice(
    reservation_id: str = Path(...),
    current_user: UserInDB = Depends(get_current_user),
):
    _assert_own_reservation(current_user, reservation_id)
    inv = hotel.invoices.get(reservation_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv.to_dict()


# ══════════════════════════════════════════════════════════════
#  📊 Reports (Finance/Manager เท่านั้น)
# ══════════════════════════════════════════════════════════════

@app.get("/reports/daily-occupancy", tags=["📊 Reports"],
         summary="รายงานสถานะห้องวันนี้ (Staff)")
def daily_occupancy(
    current_user: UserInDB = Depends(require_permission("report:occupancy")),
):
    return hotel.report_daily_occupancy()


@app.get("/reports/monthly-revenue", tags=["📊 Reports"],
         summary="รายงานรายได้รายเดือน (Finance/Manager)")
def monthly_revenue(
    year:  int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: UserInDB = Depends(require_permission("report:revenue")),
):
    return hotel.report_monthly_revenue(year, month)


@app.get("/reports/cancellations", tags=["📊 Reports"],
         summary="รายงานยกเลิกรายไตรมาส (Finance/Manager)")
def cancellation_report(
    year:    int = Query(..., ge=2020, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    current_user: UserInDB = Depends(require_permission("report:cancellation")),
):
    return hotel.report_cancellations(year, quarter)


# ══════════════════════════════════════════════════════════════
#  📋 Audit Log (Staff เท่านั้น)
# ══════════════════════════════════════════════════════════════

@app.get("/audit-log", tags=["📋 Audit Log"], summary="ดู Audit Log (Staff)")
def get_audit_log(
    action:     Optional[str] = Query(None),
    target_ref: Optional[str] = Query(None),
    current_user: UserInDB = Depends(require_permission("auditlog:read")),
):
    return AuditLog.get_entries(action, target_ref)


# ══════════════════════════════════════════════════════════════
#  🔧 Dev
# ══════════════════════════════════════════════════════════════

@app.get("/dev/seed-info", tags=["🔧 Dev"], summary="ดู seed data + test accounts")
def seed_info():
    return {
        "test_accounts": {
            "staff": [
                {"username": "frontdesk01", "password": "front1234",   "role": "FrontDesk"},
                {"username": "frontdesk02", "password": "front5678",   "role": "FrontDesk"},
                {"username": "finance01",   "password": "finance1234", "role": "Finance"},
                {"username": "manager01",   "password": "manager1234", "role": "Manager"},
            ],
            "guests": [
                {"email": "pangpang@email.com", "password": "guest1234", "guest_id": _g1.guest_id},
                {"email": "aunaun@email.com",   "password": "guest1234", "guest_id": _g2.guest_id},
                {"email": "toytoy@email.com",   "password": "guest1234", "guest_id": _g3.guest_id},
            ],
        },
        "rooms": [
            {"room_id": r.resource_id, "type": r.room_type.value,
             "price": r.price_per_night, "status": r.room_state.value}
            for r in hotel.rooms.values()
        ],
    }