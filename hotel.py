from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum


# ─────────────────────────────────────────
#  Enums
# ─────────────────────────────────────────

class RoomType(str, Enum):
    STANDARD = "STANDARD"
    DELUXE = "DELUXE"


class RoomState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    OCCUPIED = "Occupied"
    MAINTENANCE = "Maintenance"


class ReservationStatus(str, Enum):
    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    CHECKED_IN = "CheckedIn"
    COMPLETED = "Completed"


class InvoiceStatus(str, Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    VOIDED = "Voided"


class PaymentStatus(str, Enum):
    SUCCESS = "Success"
    FAILED = "Failed"
    REFUNDED = "Refunded"


PRICE_PER_NIGHT: Dict[RoomType, float] = {
    RoomType.STANDARD: 1000.0,
    RoomType.DELUXE:   2000.0,
}

CANCELLATION_FREE_HOURS = 48  # ยกเลิกฟรีก่อน check-in อย่างน้อย 48 ชั่วโมง


# ─────────────────────────────────────────
#  AuditLog
# ─────────────────────────────────────────

class AuditLog:
    _entries: List[dict] = []

    @classmethod
    def logAuditAction(cls, actor_id: str, action: str, target_ref: str) -> None:
        entry = {
            "timestamp": datetime.now(),
            "actor_id": actor_id,
            "action": action,
            "target_ref": target_ref,
        }
        cls._entries.append(entry)
        print(f"[AUDIT] {entry['timestamp']} | {actor_id} | {action} | {target_ref}")

    @classmethod
    def getEntries(cls) -> List[dict]:
        return cls._entries


# ─────────────────────────────────────────
#  Payment
# ─────────────────────────────────────────

class Payment:
    _running_no = 1

    def __init__(self, amount: float):
        self.payment_id = f"PAY{Payment._running_no:04d}"
        Payment._running_no += 1
        self.amount = amount
        self.paid_at: Optional[datetime] = None
        self.status = PaymentStatus.SUCCESS

    def processPayment(self) -> bool:
        self.paid_at = datetime.now()
        self.status = PaymentStatus.SUCCESS
        print(f"[Payment] {self.payment_id} — charged {self.amount:.2f} ✅")
        return True

    def processRefund(self, refund_amount: float) -> bool:
        self.status = PaymentStatus.REFUNDED
        print(f"[Payment] {self.payment_id} — refunded {refund_amount:.2f} ✅")
        return True


class CreditCard(Payment):
    def __init__(self, amount: float, card_number: str, expiry_date: str, cvv: str):
        super().__init__(amount)
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.cvv = cvv

    def verifyCard(self) -> bool:
        return len(self.card_number) == 16


class BankTransfer(Payment):
    def __init__(self, amount: float, bank_name: str, ref_number: str):
        super().__init__(amount)
        self.bank_name = bank_name
        self.ref_number = ref_number


class Cash(Payment):
    def __init__(self, amount: float, receive_amount: float):
        super().__init__(amount)
        self.receive_amount = receive_amount
        self.change = receive_amount - amount


# ─────────────────────────────────────────
#  Discount
# ─────────────────────────────────────────

class Discount:
    def __init__(self, discount_rate: float, discount_code: str = ""):
        self.discount_rate = discount_rate      # เช่น 10 = 10%
        self.discount_code = discount_code

    def applyDiscount(self, total_amount: float) -> float:
        """คืนค่า total หลังหักส่วนลด"""
        discount_value = total_amount * (self.discount_rate / 100)
        return total_amount - discount_value


# ─────────────────────────────────────────
#  Invoice
# ─────────────────────────────────────────

class Invoice:
    _running_no = 1

    def __init__(self, reservation: "Reservation"):
        self.invoice_no = f"INV{Invoice._running_no:04d}"
        Invoice._running_no += 1
        self.reservation = reservation
        self.issued_date = datetime.now()
        self.tax_amount = reservation.total_amount * 0.07
        self.grand_total = reservation.total_amount + self.tax_amount
        self.status = InvoiceStatus.UNPAID
        self.total_paid: float = 0.0
        self.payments: List[Payment] = []

    def validate(self) -> bool:
        return self.status != InvoiceStatus.VOIDED

    def updateStatus(self, amount_paid: float) -> None:
        self.total_paid += amount_paid
        if self.total_paid >= self.grand_total:
            self.status = InvoiceStatus.PAID

    def voidInvoice(self) -> None:
        self.status = InvoiceStatus.VOIDED
        print(f"[Invoice] {self.invoice_no} — voided")

    def applyPenalty(self, penalty_amount: float) -> float:
        """
        หักค่าปรับออกจาก grand_total แล้วคืนจำนวนที่ต้อง refund
        """
        refund_amount = self.grand_total - penalty_amount
        print(f"[Invoice] {self.invoice_no} — penalty {penalty_amount:.2f}, refund {refund_amount:.2f}")
        return max(refund_amount, 0.0)


# ─────────────────────────────────────────
#  Room
# ─────────────────────────────────────────

class Room:
    def __init__(self, room_number: str, floor: int, room_type: RoomType):
        self.room_number = room_number
        self.floor = floor
        self.room_type = room_type
        self.status = RoomState.AVAILABLE
        self.status_updated_at = datetime.now()

    def changeStatus(self, new_status: RoomState) -> bool:
        self.status = new_status
        self.status_updated_at = datetime.now()
        print(f"[Room] {self.room_number} → {new_status.value}")
        return True

    def isAvailable(self, check_in: datetime, check_out: datetime,
                    reservations: List["Reservation"]) -> bool:
        for r in reservations:
            if r.room == self and r.status == ReservationStatus.ACTIVE:
                if check_in < r.check_out_date and check_out > r.check_in_date:
                    return False
        return True

    def cleanRoom(self) -> None:
        self.changeStatus(RoomState.AVAILABLE)


class ReservedRoom(Room):
    def __init__(self, room_number: str, floor: int, room_type: RoomType,
                 extra_bed: bool = False):
        super().__init__(room_number, floor, room_type)
        self.status_name = RoomState.RESERVED
        self.updated_at = datetime.now()
        self.extra_bed = extra_bed

    def getDurationMinutes(self, check_in: datetime, check_out: datetime) -> int:
        return int((check_out - check_in).total_seconds() / 60)


# ─────────────────────────────────────────
#  Reservation
# ─────────────────────────────────────────

class Reservation:
    def __init__(self, reservation_no: str, guest_name: str, room: Room,
                 check_in_date: datetime, check_out_date: datetime):
        self.reservation_no = reservation_no
        self.booking_date = datetime.now()
        self.guest_name = guest_name
        self.room = room
        self.check_in_date = check_in_date
        self.check_out_date = check_out_date
        self.total_amount: float = 0.0
        self.status = ReservationStatus.ACTIVE
        self.discounts: List[Discount] = []

    # ── ราคา ─────────────────────────────

    def calculateTotal(self) -> None:
        nights = (self.check_out_date - self.check_in_date).days
        rate = PRICE_PER_NIGHT[self.room.room_type]
        self.total_amount = nights * rate

    def applyDiscount(self, discount: Discount) -> None:
        self.discounts.append(discount)
        self.total_amount = discount.applyDiscount(self.total_amount)

    def getFirstNightRate(self) -> float:
        """คืนราคาค่าห้องคืนแรก (ไม่รวมภาษี) ใช้เป็นค่าปรับ"""
        return PRICE_PER_NIGHT[self.room.room_type]

    # ── เวลา ──────────────────────────────

    def getHoursUntilCheckIn(self) -> float:
        delta = self.check_in_date - datetime.now()
        return delta.total_seconds() / 3600

    # ── สถานะ ─────────────────────────────

    def cancelBooking(self) -> None:
        self.status = ReservationStatus.CANCELLED
        print(f"[Reservation] {self.reservation_no} — cancelled")


# ─────────────────────────────────────────
#  Result DTOs
# ─────────────────────────────────────────

class ReservationResult:
    def __init__(self, status: str,
                 reservation_no: Optional[str] = None,
                 room_number: Optional[str] = None,
                 total_amount: Optional[float] = None,
                 message: Optional[str] = None):
        self.status = status
        self.reservation_no = reservation_no
        self.room_number = room_number
        self.total_amount = total_amount
        self.message = message

    def __repr__(self):
        if self.status == "success":
            return (f"ReservationResult(success | {self.reservation_no} "
                    f"| room {self.room_number} | {self.total_amount:.2f} THB)")
        return f"ReservationResult(fail | {self.message})"


class CancellationResult:
    def __init__(self, status: str,
                 reservation_no: Optional[str] = None,
                 penalty_amount: float = 0.0,
                 refund_amount: float = 0.0,
                 message: Optional[str] = None):
        self.status = status
        self.reservation_no = reservation_no
        self.penalty_amount = penalty_amount
        self.refund_amount = refund_amount
        self.message = message

    def __repr__(self):
        if self.status == "success":
            return (f"CancellationResult(success | {self.reservation_no} "
                    f"| penalty {self.penalty_amount:.2f} | refund {self.refund_amount:.2f} THB)")
        return f"CancellationResult(fail | {self.message})"


# ─────────────────────────────────────────
#  UserAccount / Guest / Staff
# ─────────────────────────────────────────

class UserAccount:
    def __init__(self, user_id: int, username: str, password: str, email: str):
        self.user_id = user_id
        self.username = username
        self._password = password
        self.email = email

    def login(self, password: str) -> bool:
        return self._password == password

    def logout(self) -> None:
        print(f"[UserAccount] {self.username} logged out")


class Guest(UserAccount):
    def __init__(self, user_id: int, username: str, password: str, email: str,
                 phone_number: str, address: str):
        super().__init__(user_id, username, password, email)
        self.phone_number = phone_number
        self.address = address

    def register(self) -> None:
        print(f"[Guest] {self.username} registered")

    def viewBookingHistory(self, reservations: List[Reservation]) -> List[Reservation]:
        return [r for r in reservations if r.guest_name == self.username]


class Staff(UserAccount):
    def __init__(self, user_id: int, username: str, password: str, email: str,
                 staff_id: str, salary: float, position: str):
        super().__init__(user_id, username, password, email)
        self.staff_id = staff_id
        self.salary = salary
        self.position = position

    def checkInWork(self) -> None:
        print(f"[Staff] {self.username} checked in at {datetime.now()}")


class Manager(Staff):
    def approveBudget(self, amount: float) -> bool:
        print(f"[Manager] Budget {amount:.2f} approved")
        return True

    def viewReports(self) -> None:
        print("[Manager] Viewing reports")


class FrontDesk(Staff):
    def createReservation(self) -> None:
        print("[FrontDesk] Creating reservation")

    def checkInGuest(self) -> None:
        print("[FrontDesk] Checking in guest")


class Finance(Staff):
    def issueInvoice(self) -> None:
        print("[Finance] Issuing invoice")

    def manageExpenses(self) -> None:
        print("[Finance] Managing expenses")

    def incomeReport(self) -> None:
        print("[Finance] Generating income report")


# ─────────────────────────────────────────
#  Hotel  (Facade / Coordinator)
# ─────────────────────────────────────────

class Hotel:
    def __init__(self):
        self.rooms: List[Room] = []
        self.reservations: List[Reservation] = []
        self.invoices: Dict[str, Invoice] = {}   # reservation_no → Invoice
        self.staff: List[Staff] = []
        self._running_no = 1

        # seed rooms
        for i in range(1, 6):
            self.rooms.append(Room(str(i), 1, RoomType.STANDARD))
        for i in range(6, 9):
            self.rooms.append(Room(str(i), 2, RoomType.DELUXE))

    # ── helpers ───────────────────────────

    def _generateReservationNo(self) -> str:
        no = f"RES{self._running_no:04d}"
        self._running_no += 1
        return no

    def _findReservation(self, reservation_no: str) -> Optional[Reservation]:
        for r in self.reservations:
            if r.reservation_no == reservation_no:
                return r
        return None

    def _findAvailableRoom(self, room_type: RoomType,
                           check_in: datetime, check_out: datetime) -> Optional[Room]:
        for room in self.rooms:
            if room.room_type == room_type:
                if room.isAvailable(check_in, check_out, self.reservations):
                    return room
        return None

    def getInvoice(self, reservation_no: str) -> Optional[Invoice]:
        return self.invoices.get(reservation_no)

    # ── createReservation ─────────────────

    def createReservation(self, guest_name: str, room_type: RoomType,
                          check_in: datetime, check_out: datetime,
                          discount: float = 0) -> ReservationResult:

        if check_out <= check_in:
            return ReservationResult("fail", message="Invalid date range")

        room = self._findAvailableRoom(room_type, check_in, check_out)
        if not room:
            return ReservationResult("fail", message="No room available")

        room.changeStatus(RoomState.RESERVED)

        reservation_no = self._generateReservationNo()
        reservation = Reservation(reservation_no, guest_name, room, check_in, check_out)
        reservation.calculateTotal()

        if discount > 0:
            reservation.applyDiscount(Discount(discount))

        self.reservations.append(reservation)

        invoice = Invoice(reservation)
        self.invoices[reservation_no] = invoice

        payment = Payment(invoice.grand_total)
        if not payment.processPayment():
            reservation.cancelBooking()
            invoice.voidInvoice()
            room.changeStatus(RoomState.AVAILABLE)
            return ReservationResult("fail", message="Payment failed")

        invoice.updateStatus(invoice.grand_total)
        invoice.payments.append(payment)

        AuditLog.logAuditAction("system", "CREATE_RESERVATION", reservation_no)

        return ReservationResult(
            "success",
            reservation_no=reservation.reservation_no,
            room_number=room.room_number,
            total_amount=reservation.total_amount,
        )

    # ── cancelReservation ─────────────────

    def cancelReservation(self, reservation_no: str,
                          actor_id: str = "system") -> CancellationResult:
        """
        เงื่อนไขการยกเลิก:
          - ยกเลิกก่อน check-in >= 48 ชม. → ยกเลิกฟรี (full refund)
          - ยกเลิกก่อน check-in < 48 ชม.  → คิดค่าปรับ = ค่าห้องคืนแรก
        """

        # 1. ตรวจสอบการจอง
        reservation = self._findReservation(reservation_no)

        if not reservation:
            return CancellationResult("fail", message="Reservation not found")

        if reservation.status == ReservationStatus.CANCELLED:
            return CancellationResult("fail", reservation_no=reservation_no,
                                      message="Already cancelled")

        # 2. ตรวจสอบเงื่อนไข Penalty
        hours_left = reservation.getHoursUntilCheckIn()
        invoice = self.getInvoice(reservation_no)
        penalty_amount = 0.0
        refund_amount = 0.0

        if hours_left >= CANCELLATION_FREE_HOURS:
            # ✅ ยกเลิกฟรี — void invoice + full refund
            print(f"[Hotel] {reservation_no} — free cancellation "
                  f"({hours_left:.1f} hrs before check-in)")
            if invoice:
                invoice.voidInvoice()
            refund_amount = reservation.total_amount
            payment = Payment(refund_amount)
            payment.processRefund(refund_amount)

        else:
            # ⚠️ คิดค่าปรับ = ค่าห้องคืนแรก
            print(f"[Hotel] {reservation_no} — late cancellation "
                  f"({hours_left:.1f} hrs before check-in) → penalty applied")
            penalty_amount = reservation.getFirstNightRate()
            if invoice:
                refund_amount = invoice.applyPenalty(penalty_amount)
            else:
                refund_amount = max(reservation.total_amount - penalty_amount, 0.0)
            payment = Payment(refund_amount)
            payment.processRefund(refund_amount)

        # 3. ยกเลิกการจองในระบบ
        reservation.cancelBooking()

        # 4. อัปเดตสถานะห้อง
        reservation.room.changeStatus(RoomState.AVAILABLE)

        # 5. บันทึก Audit Log
        AuditLog.logAuditAction(actor_id, "CANCEL_RESERVATION", reservation_no)

        return CancellationResult(
            "success",
            reservation_no=reservation_no,
            penalty_amount=penalty_amount,
            refund_amount=refund_amount,
        )

    # ── checkIn / checkOut ────────────────

    def checkIn(self, reservation_no: str) -> bool:
        reservation = self._findReservation(reservation_no)
        if not reservation or reservation.status != ReservationStatus.ACTIVE:
            return False
        reservation.status = ReservationStatus.CHECKED_IN
        reservation.room.changeStatus(RoomState.OCCUPIED)
        AuditLog.logAuditAction("system", "CHECK_IN", reservation_no)
        return True

    def checkOut(self, reservation_no: str) -> bool:
        reservation = self._findReservation(reservation_no)
        if not reservation or reservation.status != ReservationStatus.CHECKED_IN:
            return False
        reservation.status = ReservationStatus.COMPLETED
        reservation.room.changeStatus(RoomState.AVAILABLE)
        AuditLog.logAuditAction("system", "CHECK_OUT", reservation_no)
        return True

    # ── generateIncomeReport ──────────────

    def generateIncomeReport(self, start_date: datetime, end_date: datetime) -> dict:
        total = sum(
            r.total_amount
            for r in self.reservations
            if r.status != ReservationStatus.CANCELLED
            and start_date <= r.booking_date <= end_date
        )
        return {"start": start_date, "end": end_date, "total_income": total}


# ─────────────────────────────────────────
#  Quick Demo
# ─────────────────────────────────────────

if __name__ == "__main__":
    hotel = Hotel()

    check_in = datetime(2025, 6, 10, 14, 0)
    check_out = datetime(2025, 6, 13, 12, 0)

    # สร้างการจอง
    result = hotel.createReservation("Alice", RoomType.STANDARD, check_in, check_out)
    print(result)

    res_no = result.reservation_no

    # ── ทดสอบ 1: ยกเลิกฟรี (จำลองว่า check-in อยู่ไกล) ──
    cancel1 = hotel.cancelReservation(res_no)
    print(cancel1)

    # สร้างการจองใหม่สำหรับทดสอบ late cancel
    result2 = hotel.createReservation("Bob", RoomType.DELUXE, check_in, check_out)
    print(result2)

    # จำลอง late cancel โดยตั้ง check_in ให้ใกล้มาก
    reservation2 = hotel._findReservation(result2.reservation_no)
    reservation2.check_in_date = datetime.now().replace(
        hour=datetime.now().hour + 1,
        minute=0, second=0, microsecond=0
    )

    cancel2 = hotel.cancelReservation(result2.reservation_no)
    print(cancel2)
