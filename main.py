"""
Hotel Reservation API
─────────────────────
วิธีรัน:
    pip install fastapi uvicorn
    uvicorn main:app --reload
    uvicorn checkIn:app --reload

Swagger UI: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from hotel import (
    Hotel, RoomType, RoomState, ReservationStatus,
    InvoiceStatus, AuditLog, CANCELLATION_FREE_HOURS
)

# ─────────────────────────────────────────
#  App & Shared State
# ─────────────────────────────────────────

app = FastAPI(
    title="🏨 Hotel Reservation API",
    description="""
## Hotel Reservation System

ระบบจัดการการจองโรงแรม รองรับ:

- 🛏️ **Rooms** — ดูสถานะห้องทั้งหมด / เปลี่ยนสถานะห้อง
- 📅 **Reservations** — สร้าง / ดู / ยกเลิกการจอง
- 🧾 **Invoices** — ดูใบแจ้งหนี้
- 📋 **Audit Log** — ดู log การกระทำทั้งหมด
- 📊 **Reports** — รายงานรายได้

### เงื่อนไขการยกเลิก
| เวลาก่อน Check-in | ค่าปรับ |
|---|---|
| ≥ 48 ชั่วโมง | ฟรี (Full Refund) |
| < 48 ชั่วโมง | เท่ากับค่าห้องคืนแรก |
    """,
    version="1.0.0",
)

hotel = Hotel()


# ─────────────────────────────────────────
#  Request / Response Schemas
# ─────────────────────────────────────────

class CreateReservationRequest(BaseModel):
    guest_name: str = Field(..., description="ชื่อผู้เข้าพัก")
    room_type: RoomType = Field(..., description="ประเภทห้อง")
    check_in_date: datetime = Field(..., description="วันเช็คอิน")
    check_out_date: datetime = Field(..., description="วันเช็คเอาท์")
    discount_percent: float = Field(0, ge=0, le=100, description="ส่วนลด (%)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "guest_name": "สมชาย ใจดี",
                    "room_type": "STANDARD",
                    "check_in_date": "2025-06-10T14:00:00",
                    "check_out_date": "2025-06-13T12:00:00",
                    "discount_percent": 0,
                }
            ]
        }
    }


class CancelReservationRequest(BaseModel):
    actor_id: str = Field("staff_001", description="รหัสพนักงานที่ดำเนินการ")

    model_config = {
        "json_schema_extra": {
            "examples": [{"actor_id": "staff_001"}]
        }
    }


class UpdateRoomStatusRequest(BaseModel):
    new_status: RoomState

    model_config = {
        "json_schema_extra": {
            "examples": [{"new_status": "Maintenance"}]
        }
    }


class IncomeReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2025-01-01T00:00:00",
                    "end_date": "2025-12-31T23:59:59",
                }
            ]
        }
    }


# ─────────────────────────────────────────
#  🛏️ Rooms
# ─────────────────────────────────────────

@app.get(
    "/rooms",
    tags=["🛏️ Rooms"],
    summary="ดูสถานะห้องทั้งหมด",
)
def list_rooms(
    room_type: Optional[RoomType] = Query(None, description="กรองตามประเภทห้อง"),
    status: Optional[RoomState] = Query(None, description="กรองตามสถานะห้อง"),
):
    rooms = hotel.rooms
    if room_type:
        rooms = [r for r in rooms if r.room_type == room_type]
    if status:
        rooms = [r for r in rooms if r.status == status]

    return [
        {
            "room_number": r.room_number,
            "floor": r.floor,
            "room_type": r.room_type,
            "status": r.status,
            "price_per_night": 1000 if r.room_type == RoomType.STANDARD else 2000,
            "status_updated_at": r.status_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for r in rooms
    ]


@app.patch(
    "/rooms/{room_number}/status",
    tags=["🛏️ Rooms"],
    summary="เปลี่ยนสถานะห้อง (Manual)",
)
def update_room_status(
    room_number: str = Path(..., examples=["1"]),
    body: UpdateRoomStatusRequest = ...,
):
    room = next((r for r in hotel.rooms if r.room_number == room_number), None)
    if not room:
        raise HTTPException(404, detail=f"Room {room_number} not found")

    room.changeStatus(body.new_status)
    AuditLog.logAuditAction("staff", f"MANUAL_STATUS_{body.new_status.value.upper()}", f"ROOM-{room_number}")

    return {
        "room_number": room_number,
        "new_status": room.status,
        "updated_at": room.status_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─────────────────────────────────────────
#  📅 Reservations
# ─────────────────────────────────────────

@app.post(
    "/reservations",
    tags=["📅 Reservations"],
    summary="สร้างการจองใหม่",
    status_code=201,
)
def create_reservation(body: CreateReservationRequest):
    result = hotel.createReservation(
        guest_name=body.guest_name,
        room_type=body.room_type,
        check_in=body.check_in_date,
        check_out=body.check_out_date,
        discount=body.discount_percent,
    )

    if result.status != "success":
        raise HTTPException(400, detail=result.message)

    invoice = hotel.getInvoice(result.reservation_no)
    return {
        "status": "success",
        "reservation_no": result.reservation_no,
        "room_number": result.room_number,
        "room_type": body.room_type,
        "guest_name": body.guest_name,
        "check_in_date": body.check_in_date.strftime("%Y-%m-%d %H:%M"),
        "check_out_date": body.check_out_date.strftime("%Y-%m-%d %H:%M"),
        "nights": (body.check_out_date - body.check_in_date).days,
        "total_amount": result.total_amount,
        "invoice_no": invoice.invoice_no if invoice else None,
        "grand_total_with_tax": invoice.grand_total if invoice else None,
    }


@app.get(
    "/reservations",
    tags=["📅 Reservations"],
    summary="ดูรายการจองทั้งหมด",
)
def list_reservations(
    status: Optional[ReservationStatus] = Query(None, description="กรองตามสถานะ"),
    guest_name: Optional[str] = Query(None, description="ค้นหาตามชื่อแขก"),
):
    reservations = hotel.reservations

    if status:
        reservations = [r for r in reservations if r.status == status]
    if guest_name:
        reservations = [r for r in reservations if guest_name.lower() in r.guest_name.lower()]

    return [
        {
            "reservation_no": r.reservation_no,
            "guest_name": r.guest_name,
            "room_number": r.room.room_number,
            "room_type": r.room.room_type,
            "check_in_date": r.check_in_date.strftime("%Y-%m-%d %H:%M"),
            "check_out_date": r.check_out_date.strftime("%Y-%m-%d %H:%M"),
            "nights": (r.check_out_date - r.check_in_date).days,
            "total_amount": r.total_amount,
            "status": r.status,
            "booking_date": r.booking_date.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for r in reservations
    ]


@app.get(
    "/reservations/{reservation_no}",
    tags=["📅 Reservations"],
    summary="ดูรายละเอียดการจอง",
)
def get_reservation(reservation_no: str = Path(..., examples=["RES0001"])):
    r = hotel._findReservation(reservation_no)
    if not r:
        raise HTTPException(404, detail="Reservation not found")

    invoice = hotel.getInvoice(reservation_no)
    hours_left = r.getHoursUntilCheckIn()

    return {
        "reservation_no": r.reservation_no,
        "guest_name": r.guest_name,
        "room_number": r.room.room_number,
        "room_type": r.room.room_type,
        "check_in_date": r.check_in_date.strftime("%Y-%m-%d %H:%M"),
        "check_out_date": r.check_out_date.strftime("%Y-%m-%d %H:%M"),
        "nights": (r.check_out_date - r.check_in_date).days,
        "total_amount": r.total_amount,
        "status": r.status,
        "booking_date": r.booking_date.strftime("%Y-%m-%d %H:%M:%S"),
        "invoice_no": invoice.invoice_no if invoice else None,
        "invoice_status": invoice.status if invoice else None,
        "grand_total_with_tax": invoice.grand_total if invoice else None,
        "cancellation_info": {
            "hours_until_checkin": round(hours_left, 1),
            "is_free_cancellation": hours_left >= CANCELLATION_FREE_HOURS,
            "penalty_if_cancelled_now": r.getFirstNightRate() if hours_left < CANCELLATION_FREE_HOURS else 0,
            "free_cancellation_deadline": f"ยกเลิกฟรีได้ถึง {CANCELLATION_FREE_HOURS} ชม. ก่อนเช็คอิน",
        },
    }


@app.post(
    "/reservations/{reservation_no}/cancel",
    tags=["📅 Reservations"],
    summary="ยกเลิกการจอง",
)
def cancel_reservation(
    reservation_no: str = Path(..., examples=["RES0001"]),
    body: CancelReservationRequest = ...,
):
    result = hotel.cancelReservation(reservation_no, actor_id=body.actor_id)

    if result.status != "success":
        raise HTTPException(400, detail=result.message)

    is_free = result.penalty_amount == 0
    return {
        "status": "cancelled",
        "reservation_no": result.reservation_no,
        "cancellation_type": "free" if is_free else "with_penalty",
        "penalty_amount": result.penalty_amount,
        "refund_amount": result.refund_amount,
        "message": (
            "ยกเลิกสำเร็จ — คืนเงินเต็มจำนวน"
            if is_free
            else f"ยกเลิกสำเร็จ — หักค่าปรับ {result.penalty_amount:.2f} บาท (ค่าห้องคืนแรก)"
        ),
    }


@app.post(
    "/reservations/{reservation_no}/checkin",
    tags=["📅 Reservations"],
    summary="เช็คอิน",
)
def check_in(reservation_no: str = Path(..., examples=["RES0001"])):
    success = hotel.checkIn(reservation_no)
    if not success:
        raise HTTPException(400, detail="Check-in failed — reservation not found or not in ACTIVE status")
    return {"status": "checked_in", "reservation_no": reservation_no}


@app.post(
    "/reservations/{reservation_no}/checkout",
    tags=["📅 Reservations"],
    summary="เช็คเอาท์",
)
def check_out(reservation_no: str = Path(..., examples=["RES0001"])):
    success = hotel.checkOut(reservation_no)
    if not success:
        raise HTTPException(400, detail="Check-out failed — reservation not found or not in CHECKED_IN status")
    return {"status": "checked_out", "reservation_no": reservation_no}


# ─────────────────────────────────────────
#  🧾 Invoices
# ─────────────────────────────────────────

@app.get(
    "/invoices/{reservation_no}",
    tags=["🧾 Invoices"],
    summary="ดูใบแจ้งหนี้ตามเลขการจอง",
)
def get_invoice(reservation_no: str = Path(..., examples=["RES0001"])):
    invoice = hotel.getInvoice(reservation_no)
    if not invoice:
        raise HTTPException(404, detail="Invoice not found")

    r = invoice.reservation
    return {
        "invoice_no": invoice.invoice_no,
        "reservation_no": reservation_no,
        "guest_name": r.guest_name,
        "issued_date": invoice.issued_date.strftime("%Y-%m-%d %H:%M:%S"),
        "subtotal": r.total_amount,
        "tax_amount": round(invoice.tax_amount, 2),
        "grand_total": round(invoice.grand_total, 2),
        "total_paid": invoice.total_paid,
        "status": invoice.status,
        "payments": [
            {
                "payment_id": p.payment_id,
                "amount": p.amount,
                "status": p.status,
                "paid_at": p.paid_at.strftime("%Y-%m-%d %H:%M:%S") if p.paid_at else None,
            }
            for p in invoice.payments
        ],
    }


# ─────────────────────────────────────────
#  📋 Audit Log
# ─────────────────────────────────────────

@app.get(
    "/audit-log",
    tags=["📋 Audit Log"],
    summary="ดู Audit Log ทั้งหมด",
)
def get_audit_log(
    action: Optional[str] = Query(None, description="กรองตาม action เช่น CANCEL_RESERVATION"),
    target_ref: Optional[str] = Query(None, description="กรองตาม reservation_no เช่น RES0001"),
):
    entries = AuditLog.getEntries()

    if action:
        entries = [e for e in entries if action.upper() in e["action"].upper()]
    if target_ref:
        entries = [e for e in entries if target_ref.upper() in e["target_ref"].upper()]

    return [
        {
            "timestamp": e["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "actor_id": e["actor_id"],
            "action": e["action"],
            "target_ref": e["target_ref"],
        }
        for e in entries
    ]


# ─────────────────────────────────────────
#  📊 Reports
# ─────────────────────────────────────────

@app.post(
    "/reports/income",
    tags=["📊 Reports"],
    summary="รายงานรายได้ตามช่วงวันที่",
)
def income_report(body: IncomeReportRequest):
    report = hotel.generateIncomeReport(body.start_date, body.end_date)
    active_reservations = [
        r for r in hotel.reservations
        if r.status != ReservationStatus.CANCELLED
        and body.start_date <= r.booking_date <= body.end_date
    ]
    return {
        "start_date": body.start_date.strftime("%Y-%m-%d"),
        "end_date": body.end_date.strftime("%Y-%m-%d"),
        "total_reservations": len(active_reservations),
        "total_income": report["total_income"],
        "total_income_with_tax": round(report["total_income"] * 1.07, 2),
    }