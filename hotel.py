"""
Hotel Reservation System — hotel.py
Business Logic Layer
"""

import math
import hashlib
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from enum import Enum

# ══════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════

PRICE: Dict[str, float] = {
    "STANDARD":  1500.0,
    "DELUXE":    2200.0,
    "EXTRA_BED":  800.0,
}
DEPOSIT_NORMAL       = 1000.0
DEPOSIT_NOSHOW       = 2000.0
VAT_RATE             = 0.07
MAX_ADVANCE_DAYS     = 120
HOLD_MIN_ONLINE      = 15
HOLD_MIN_STAFF       = 30
FREE_CANCEL_HOURS    = 48
MAX_ACTIVE_RES       = 2
ACTIVE_RES_DAYS      = 60
NOSHOW_CUTOFF_HOUR   = 23
NOSHOW_THRESHOLD     = 2
NOSHOW_WINDOW_DAYS   = 365
EARLY_BIRD_MIN_DAYS  = 30
LONG_STAY_MIN_NIGHTS = 3


# ══════════════════════════════════════════════════════════════
#  Enums
# ══════════════════════════════════════════════════════════════

class RoomType(str, Enum):
    STANDARD = "STANDARD"
    DELUXE   = "DELUXE"

class RoomState(str, Enum):
    AVAILABLE   = "Available"
    HOLD        = "Hold"
    OCCUPIED    = "Occupied"
    CLEANING    = "Cleaning"
    MAINTENANCE = "Maintenance"

class ReservationStatus(str, Enum):
    DRAFT       = "Draft"
    CONFIRMED   = "Confirmed"
    CHECKED_IN  = "CheckedIn"
    CHECKED_OUT = "CheckedOut"
    CANCELLED   = "Cancelled"
    NO_SHOW     = "NoShow"

class PaymentStatus(str, Enum):
    INITIATED = "Initiated"
    PENDING   = "Pending"
    SUCCESS   = "Success"
    FAILED    = "Failed"
    REFUNDED  = "Refunded"

class PaymentType(str, Enum):
    DEPOSIT = "Deposit"
    BALANCE = "Balance"
    REFUND  = "Refund"
    PENALTY = "Penalty"

class BookingChannel(str, Enum):
    WEB     = "Web"
    PHONE   = "Phone"
    WALK_IN = "WalkIn"

class DiscountType(str, Enum):
    EARLY_BIRD = "EarlyBird"
    LONG_STAY  = "LongStay"
    CORPORATE  = "Corporate"
    NONE       = "None"

class ResourceStatus(str, Enum):
    AVAILABLE   = "Available"
    ALLOCATED   = "Allocated"
    UNAVAILABLE = "Unavailable"

class NotificationEvent(str, Enum):
    BOOKING_CONFIRMED = "BookingConfirmed"
    HOLD_EXPIRING     = "HoldExpiring"
    CHECKIN_REMINDER  = "CheckInReminder"
    CHECKOUT_SUMMARY  = "CheckOutSummary"
    NO_SHOW           = "NoShow"


# ══════════════════════════════════════════════════════════════
#  AuditLog
# ══════════════════════════════════════════════════════════════

class AuditLog:
    _entries: List[dict] = []

    @classmethod
    def log(cls, actor_id: str, action: str, target_ref: str, detail: str = "") -> dict:
        entry = {
            "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actor_id":   actor_id,
            "action":     action,
            "target_ref": target_ref,
            "detail":     detail,
        }
        cls._entries.append(entry)
        return entry

    @classmethod
    def get_entries(cls, action_filter: str = None, ref_filter: str = None) -> List[dict]:
        entries = cls._entries
        if action_filter:
            entries = [e for e in entries if action_filter.upper() in e["action"].upper()]
        if ref_filter:
            entries = [e for e in entries if ref_filter.upper() in e["target_ref"].upper()]
        return entries


# ══════════════════════════════════════════════════════════════
#  Abstract: Notification  (Abstraction + Polymorphism)
# ══════════════════════════════════════════════════════════════

class AbstractNotification(ABC):
    @abstractmethod
    def send(self, recipient: str, event: NotificationEvent, payload: dict) -> bool:
        pass

    @abstractmethod
    def channel_name(self) -> str:
        pass

class EmailNotification(AbstractNotification):
    def send(self, recipient, event, payload):
        print(f"[EMAIL -> {recipient}] {event.value}: {payload.get('message','')}")
        return True
    def channel_name(self): return "Email"

class SMSNotification(AbstractNotification):
    def send(self, recipient, event, payload):
        print(f"[SMS -> {recipient}] {event.value}: {payload.get('message','')}")
        return True
    def channel_name(self): return "SMS"

class InAppNotification(AbstractNotification):
    def send(self, recipient, event, payload):
        print(f"[IN-APP -> {recipient}] {event.value}: {payload.get('message','')}")
        return True
    def channel_name(self): return "InApp"

class NotificationService:
    def __init__(self):
        self._channels: List[AbstractNotification] = [
            EmailNotification(), SMSNotification(), InAppNotification()
        ]
    def notify(self, recipient: str, event: NotificationEvent, payload: dict,
               channels: List[str] = None):
        for ch in self._channels:
            if channels is None or ch.channel_name() in channels:
                ch.send(recipient, event, payload)


# ══════════════════════════════════════════════════════════════
#  Abstract: Payment Channel  (Abstraction + Polymorphism)
# ══════════════════════════════════════════════════════════════

class AbstractPaymentChannel(ABC):
    @abstractmethod
    def process(self, amount: float, reference: str) -> Tuple[bool, str]:
        pass
    @abstractmethod
    def channel_name(self) -> str:
        pass

class CardPayment(AbstractPaymentChannel):
    def __init__(self, card_number: str = "4111111111111111", expiry: str = "12/28", cvv: str = "123"):
        self.card_number = card_number
        self.expiry = expiry
        self.cvv = cvv
    def process(self, amount, reference):
        ext = f"CARD-{reference[-6:]}-{datetime.now().strftime('%H%M%S')}"
        print(f"[Card] Charged {amount:.2f} THB | {ext}")
        return True, ext
    def channel_name(self): return "Card"

class BankTransferPayment(AbstractPaymentChannel):
    def __init__(self, bank_name: str = "KBank", proof_url: str = ""):
        self.bank_name = bank_name
        self.proof_url = proof_url
        self.verified_by: Optional[str] = None
    def process(self, amount, reference):
        ext = f"TRANSFER-{reference[-6:]}-{datetime.now().strftime('%H%M%S')}"
        print(f"[BankTransfer] Pending {amount:.2f} THB | {ext}")
        return True, ext
    def verify(self, verifier_id: str):
        self.verified_by = verifier_id
    def channel_name(self): return "BankTransfer"

class QRPayment(AbstractPaymentChannel):
    def __init__(self, wallet_provider: str = "PromptPay"):
        self.wallet_provider = wallet_provider
    def process(self, amount, reference):
        ext = f"QR-{reference[-6:]}-{datetime.now().strftime('%H%M%S')}"
        print(f"[QR/{self.wallet_provider}] Charged {amount:.2f} THB | {ext}")
        return True, ext
    def channel_name(self): return "QR"


# ══════════════════════════════════════════════════════════════
#  Abstract: Resource  (Polymorphism)
# ══════════════════════════════════════════════════════════════

class AbstractResource(ABC):
    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        self.status      = ResourceStatus.AVAILABLE

    @abstractmethod
    def is_available(self) -> bool: pass
    @abstractmethod
    def allocate(self, reference: str) -> bool: pass
    @abstractmethod
    def release(self) -> bool: pass


# ══════════════════════════════════════════════════════════════
#  Room
# ══════════════════════════════════════════════════════════════

class Room(AbstractResource):
    def __init__(self, floor: int, room_no: int, room_type: RoomType,
                 bed_type: str = "Double", smoking: bool = False):
        super().__init__(f"RM-{floor:02d}{room_no:02d}")
        self.floor             = floor
        self.room_no           = room_no
        self.room_type         = room_type
        self.bed_type          = bed_type
        self.smoking           = smoking
        self.standard_capacity = 2
        self.max_capacity      = 3
        self.maintenance_note  = ""
        self.room_state        = RoomState.AVAILABLE
        self.state_history: List[dict] = []
        self.allocated_to: Optional[str] = None

    @property
    def price_per_night(self) -> float:
        return PRICE[self.room_type.value]

    def is_available(self) -> bool:
        return self.room_state == RoomState.AVAILABLE

    def allocate(self, reservation_id: str) -> bool:
        self.change_state(RoomState.HOLD, reservation_id=reservation_id)
        self.allocated_to = reservation_id
        return True

    def release(self) -> bool:
        self.change_state(RoomState.AVAILABLE, reason="released")
        self.allocated_to = None
        return True

    def change_state(self, new_state: RoomState, actor: str = "system",
                     reason: str = "", reservation_id: str = "") -> bool:
        self.room_state = new_state
        self.status = (ResourceStatus.AVAILABLE if new_state == RoomState.AVAILABLE
                       else ResourceStatus.ALLOCATED if new_state in (RoomState.HOLD, RoomState.OCCUPIED)
                       else ResourceStatus.UNAVAILABLE)
        self.state_history.append({
            "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actor":          actor,
            "state":          new_state.value,
            "reservation_id": reservation_id,
            "reason":         reason,
        })
        print(f"[Room] {self.resource_id} -> {new_state.value}")
        return True


# ══════════════════════════════════════════════════════════════
#  ExtraBed
# ══════════════════════════════════════════════════════════════

class ExtraBed(AbstractResource):
    def __init__(self, bed_id: str):
        super().__init__(bed_id)
        self.allocated_to: Optional[str] = None

    def is_available(self) -> bool:
        return self.status == ResourceStatus.AVAILABLE

    def allocate(self, reservation_id: str) -> bool:
        if not self.is_available():
            return False
        self.status = ResourceStatus.ALLOCATED
        self.allocated_to = reservation_id
        return True

    def release(self) -> bool:
        self.status = ResourceStatus.AVAILABLE
        self.allocated_to = None
        return True


# ══════════════════════════════════════════════════════════════
#  CleaningTask
# ══════════════════════════════════════════════════════════════

class CleaningTask(AbstractResource):
    def __init__(self, task_id: str, room_id: str):
        super().__init__(task_id)
        self.room_id      = room_id
        self.created_at   = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.assigned_to: Optional[str]       = None

    def is_available(self) -> bool:
        return self.status == ResourceStatus.AVAILABLE

    def allocate(self, worker_id: str) -> bool:
        self.status = ResourceStatus.ALLOCATED
        self.assigned_to = worker_id
        return True

    def release(self) -> bool:
        self.status = ResourceStatus.AVAILABLE
        return True

    def complete(self, worker_id: str) -> bool:
        self.completed_at = datetime.now()
        self.assigned_to  = worker_id
        self.status       = ResourceStatus.UNAVAILABLE
        return True


# ══════════════════════════════════════════════════════════════
#  Discount
# ══════════════════════════════════════════════════════════════

class Discount:
    RATES = {
        DiscountType.EARLY_BIRD: 0.10,
        DiscountType.LONG_STAY:  0.12,
        DiscountType.CORPORATE:  0.08,
        DiscountType.NONE:       0.00,
    }

    def __init__(self, discount_type: DiscountType, corporate_code: str = ""):
        self.discount_type  = discount_type
        self.rate           = self.RATES[discount_type]
        self.corporate_code = corporate_code

    def apply(self, room_total: float) -> float:
        return room_total * self.rate

    @staticmethod
    def determine(check_in: datetime, nights: int, booking_date: datetime,
                  corporate_code: str = "") -> "Discount":
        candidates = []
        days_adv = (check_in.date() - booking_date.date()).days
        if days_adv >= EARLY_BIRD_MIN_DAYS:
            candidates.append(Discount(DiscountType.EARLY_BIRD))
        if nights >= LONG_STAY_MIN_NIGHTS:
            candidates.append(Discount(DiscountType.LONG_STAY))
        if corporate_code:
            candidates.append(Discount(DiscountType.CORPORATE, corporate_code))
        return max(candidates, key=lambda d: d.rate) if candidates else Discount(DiscountType.NONE)


# ══════════════════════════════════════════════════════════════
#  PaymentRecord
# ══════════════════════════════════════════════════════════════

class PaymentRecord:
    _running: Dict[str, int] = {}

    def __init__(self, reservation_id: str, amount: float,
                 payment_type: PaymentType, channel: AbstractPaymentChannel):
        date_str = datetime.now().strftime("%Y%m%d")
        PaymentRecord._running[date_str] = PaymentRecord._running.get(date_str, 0) + 1
        self.payment_id     = f"PAY-{date_str}-{PaymentRecord._running[date_str]:06d}"
        self.reservation_id = reservation_id
        self.amount         = amount
        self.payment_type   = payment_type
        self.channel        = channel
        self.status         = PaymentStatus.INITIATED
        self.external_ref   = ""
        self.created_at     = datetime.now()
        self.processed_at:  Optional[datetime] = None
        self.approved_by:   Optional[str] = None

    def execute(self) -> bool:
        self.status = PaymentStatus.PENDING
        success, ext_ref = self.channel.process(self.amount, self.payment_id)
        self.external_ref = ext_ref
        self.processed_at = datetime.now()
        self.status = PaymentStatus.SUCCESS if success else PaymentStatus.FAILED
        return success

    def refund(self, approver: str = "system") -> bool:
        self.status = PaymentStatus.REFUNDED
        self.approved_by = approver
        return True

    def to_dict(self) -> dict:
        return {
            "payment_id":   self.payment_id,
            "amount":       self.amount,
            "type":         self.payment_type.value,
            "channel":      self.channel.channel_name(),
            "status":       self.status.value,
            "external_ref": self.external_ref,
            "processed_at": self.processed_at.strftime("%Y-%m-%d %H:%M:%S") if self.processed_at else None,
        }


# ══════════════════════════════════════════════════════════════
#  Invoice
# ══════════════════════════════════════════════════════════════

class Invoice:
    _running = 1

    def __init__(self, reservation: "Reservation"):
        self.invoice_no = f"INV{Invoice._running:04d}"
        Invoice._running += 1
        r = reservation
        self.reservation  = r
        self.issued_at    = datetime.now()
        self.payments: List[PaymentRecord] = []
        self.status       = "Unpaid"

        room_total      = r.room.price_per_night * r.nights
        disc_amount     = r.discount.apply(room_total)
        room_after      = room_total - disc_amount
        extra_total     = (PRICE["EXTRA_BED"] * r.nights) if r.extra_bed else 0.0
        vat             = math.ceil((room_after + extra_total) * VAT_RATE)

        self.room_subtotal      = room_total
        self.discount_type      = r.discount.discount_type.value
        self.discount_amount    = disc_amount
        self.room_after_disc    = room_after
        self.extra_bed_subtotal = extra_total
        self.vat_amount         = vat
        self.net_total          = room_after + extra_total + vat
        self.deposit_amount     = r.deposit_amount
        self.penalty_amount     = 0.0
        self.grand_total        = self.net_total

    def add_penalty(self, penalty: float):
        self.penalty_amount += penalty
        self.grand_total    += penalty

    def update_status(self):
        paid = self.total_paid()
        if paid >= self.grand_total:
            self.status = "Paid"
        elif paid >= self.deposit_amount:
            self.status = "DepositPaid"
        elif paid > 0:
            self.status = "PartiallyPaid"

    def total_paid(self) -> float:
        return sum(p.amount for p in self.payments if p.status == PaymentStatus.SUCCESS)

    def balance_due(self) -> float:
        return max(self.grand_total - self.total_paid(), 0)

    def void(self):
        self.status = "Voided"

    def to_dict(self) -> dict:
        return {
            "invoice_no":          self.invoice_no,
            "reservation_id":      self.reservation.reservation_id,
            "room_subtotal":       self.room_subtotal,
            "discount_type":       self.discount_type,
            "discount_amount":     self.discount_amount,
            "room_after_discount": self.room_after_disc,
            "extra_bed_subtotal":  self.extra_bed_subtotal,
            "vat_amount":          self.vat_amount,
            "net_total":           self.net_total,
            "deposit_amount":      self.deposit_amount,
            "penalty_amount":      self.penalty_amount,
            "grand_total":         self.grand_total,
            "total_paid":          self.total_paid(),
            "balance_due":         self.balance_due(),
            "status":              self.status,
            "payments":            [p.to_dict() for p in self.payments],
        }


# ══════════════════════════════════════════════════════════════
#  Guest
# ══════════════════════════════════════════════════════════════

class Guest:
    _running = 1

    def __init__(self, name: str, phone: str, email: str, id_document: str = ""):
        self.guest_id      = f"GST{Guest._running:04d}"
        Guest._running    += 1
        self.name          = name
        self.phone         = phone
        self.email         = email
        self._id_document  = id_document     # Encapsulated
        self.no_show_dates: List[datetime] = []

    def get_id_document(self, requester_role: str) -> str:
        """Encapsulation: บันทึก log ทุกครั้งที่เข้าถึงข้อมูลสำคัญ"""
        if requester_role in ("FrontDesk", "Finance", "Manager"):
            AuditLog.log(requester_role, "ACCESS_ID_DOCUMENT", self.guest_id)
            return self._id_document
        return "*** RESTRICTED ***"

    def recent_no_show_count(self) -> int:
        cutoff = datetime.now() - timedelta(days=NOSHOW_WINDOW_DAYS)
        return sum(1 for d in self.no_show_dates if d >= cutoff)

    def required_deposit(self) -> float:
        return DEPOSIT_NOSHOW if self.recent_no_show_count() >= NOSHOW_THRESHOLD else DEPOSIT_NORMAL

    def record_no_show(self):
        self.no_show_dates.append(datetime.now())


# ══════════════════════════════════════════════════════════════
#  Reservation
# ══════════════════════════════════════════════════════════════

class Reservation:
    _running: Dict[str, int] = {}

    def __init__(self, guest: Guest, room: Room,
                 check_in: datetime, check_out: datetime,
                 channel: BookingChannel = BookingChannel.WEB,
                 extra_bed: bool = False,
                 corporate_code: str = "",
                 special_requests: str = ""):
        date_str = datetime.now().strftime("%Y%m%d")
        Reservation._running[date_str] = Reservation._running.get(date_str, 0) + 1
        self.reservation_id = f"RSV-{date_str}-{Reservation._running[date_str]:05d}"

        self.guest            = guest
        self.room             = room
        self.check_in         = check_in
        self.check_out        = check_out
        self.nights = (check_out.date() - check_in.date()).days
        self.channel          = channel
        self.extra_bed        = extra_bed
        self.corporate_code   = corporate_code
        self.special_requests = special_requests
        self.booking_date     = datetime.now()
        self.status           = ReservationStatus.DRAFT
        self.invoice:         Optional[Invoice]   = None
        self.payments:        List[PaymentRecord] = []
        self.history:         List[dict]          = []
        self.penalty_amount   = 0.0
        self.extra_bed_res:   Optional[ExtraBed]  = None

        hold_min = HOLD_MIN_STAFF if channel == BookingChannel.WALK_IN else HOLD_MIN_ONLINE
        self.hold_expires_at = datetime.now() + timedelta(minutes=hold_min)
        self.deposit_amount  = guest.required_deposit()
        self.discount        = Discount.determine(check_in, self.nights, self.booking_date, corporate_code)
        self._log("system", "CREATED", f"channel={channel.value}, room={room.resource_id}")

    def _log(self, actor: str, action: str, detail: str = ""):
        self.history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actor": actor, "action": action, "detail": detail,
        })

    @property
    def is_hold_expired(self) -> bool:
        return datetime.now() > self.hold_expires_at and self.status == ReservationStatus.DRAFT

    def hours_until_checkin(self) -> float:
        return (self.check_in - datetime.now()).total_seconds() / 3600

    # Encapsulation: สถานะเปลี่ยนได้ผ่าน method เท่านั้น พร้อมตรวจกฎธุรกิจ

    def confirm(self, payment: PaymentRecord) -> bool:
        if self.status != ReservationStatus.DRAFT:
            return False
        self.status = ReservationStatus.CONFIRMED
        self.payments.append(payment)
        self._log("system", "CONFIRMED", f"deposit={payment.payment_id}")
        return True

    def do_checkin(self, actor: str = "FrontDesk") -> bool:
        if self.status != ReservationStatus.CONFIRMED:
            return False
        self.status = ReservationStatus.CHECKED_IN
        self.room.change_state(RoomState.OCCUPIED, actor, reservation_id=self.reservation_id)
        self._log(actor, "CHECKED_IN")
        return True

    def do_checkout(self, actor: str = "FrontDesk") -> bool:
        if self.status != ReservationStatus.CHECKED_IN:
            return False
        self.status = ReservationStatus.CHECKED_OUT
        self.room.change_state(RoomState.CLEANING, actor, reservation_id=self.reservation_id)
        if self.extra_bed_res:
            self.extra_bed_res.release()
        self._log(actor, "CHECKED_OUT")
        return True

    def cancel(self, actor: str = "system") -> Tuple[float, float]:
        hours   = self.hours_until_checkin()
        penalty = self.room.price_per_night if hours < FREE_CANCEL_HOURS else 0.0
        self.penalty_amount = penalty
        self.status = ReservationStatus.CANCELLED
        self.room.change_state(RoomState.AVAILABLE, actor, reason="cancelled")
        if self.extra_bed_res:
            self.extra_bed_res.release()
        paid   = sum(p.amount for p in self.payments if p.status == PaymentStatus.SUCCESS)
        refund = max(paid - penalty, 0)
        self._log(actor, "CANCELLED", f"hours={hours:.1f}, penalty={penalty}, refund={refund}")
        return penalty, refund

    def mark_no_show(self, actor: str = "system") -> float:
        penalty = self.room.price_per_night
        self.penalty_amount = penalty
        self.status = ReservationStatus.NO_SHOW
        self.room.change_state(RoomState.AVAILABLE, actor, reason="no-show")
        self.guest.record_no_show()
        self._log(actor, "NO_SHOW", f"penalty={penalty}")
        return penalty


# ══════════════════════════════════════════════════════════════
#  Role & Permission System
# ══════════════════════════════════════════════════════════════

class UserRole(str, Enum):
    GUEST        = "Guest"
    FRONTDESK    = "FrontDesk"
    FINANCE      = "Finance"
    MANAGER      = "Manager"

# Use Cases ที่แต่ละ Role เข้าถึงได้ (ตาม Use Case Diagram)
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.GUEST: [
        "search_availability",
        "create_reservation",
        "cancel_reservation",
        "view_own_reservations",
        "payment",
        "apply_discount",
    ],
    UserRole.FRONTDESK: [
        "search_availability",
        "create_reservation",
        "cancel_reservation",
        "check_in",
        "check_out",
        "change_room",
        "update_room_status",
        "generate_invoice",
        "validation",
        "apply_penalty_fee",
        "view_all_reservations",
    ],
    UserRole.FINANCE: [
        "payment",
        "apply_discount",
        "update_income",
        "view_reports",
        "verify_transfer",
        "issue_refund",
    ],
    UserRole.MANAGER: [
        # Manager inherits FrontDesk permissions (generalization in diagram)
        "search_availability",
        "create_reservation",
        "cancel_reservation",
        "check_in",
        "check_out",
        "change_room",
        "update_room_status",
        "generate_invoice",
        "validation",
        "apply_penalty_fee",
        "view_all_reservations",
        # Manager extras
        "payment",
        "apply_discount",
        "update_income",
        "view_reports",
        "verify_transfer",
        "issue_refund",
        "room_maintenance",
        "approve_exception",
        "view_audit_log",
    ],
}


# ══════════════════════════════════════════════════════════════
#  Session / Token Store
# ══════════════════════════════════════════════════════════════

SESSION_TTL_MINUTES = 60

class SessionStore:
    """In-memory token store  {token -> {user_id, role, expires_at}}"""
    _sessions: Dict[str, dict] = {}

    @classmethod
    def create(cls, user_id: str, role: UserRole) -> str:
        token = secrets.token_hex(32)
        cls._sessions[token] = {
            "user_id":    user_id,
            "role":       role,
            "expires_at": datetime.now() + timedelta(minutes=SESSION_TTL_MINUTES),
        }
        return token

    @classmethod
    def get(cls, token: str) -> Optional[dict]:
        s = cls._sessions.get(token)
        if s and datetime.now() < s["expires_at"]:
            return s
        if s:
            del cls._sessions[token]   # expired
        return None

    @classmethod
    def revoke(cls, token: str):
        cls._sessions.pop(token, None)

    @classmethod
    def purge_expired(cls):
        now = datetime.now()
        expired = [t for t, s in cls._sessions.items() if now >= s["expires_at"]]
        for t in expired:
            del cls._sessions[t]


# ══════════════════════════════════════════════════════════════
#  UserAccount Hierarchy  (Inheritance >= 2 levels)
# ══════════════════════════════════════════════════════════════

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class UserAccount:
    """Level 0 — base for all users (Guest & Staff)"""
    _running = 1

    def __init__(self, username: str, email: str,
                 password: str, role: UserRole):
        self.user_id       = f"USR{UserAccount._running:04d}"
        UserAccount._running += 1
        self.username      = username
        self.email         = email
        self._pw_hash      = _hash_password(password)   # Encapsulation
        self.role          = role
        self.is_active     = True
        self.created_at    = datetime.now()

    def verify_password(self, password: str) -> bool:
        return self._pw_hash == _hash_password(password)

    def login(self, password: str) -> Tuple[bool, str]:
        """Returns (success, token|error_message)"""
        if not self.is_active:
            AuditLog.log(self.user_id, "LOGIN_BLOCKED", self.user_id, "account inactive")
            return False, "Account is inactive"
        if not self.verify_password(password):
            AuditLog.log(self.user_id, "LOGIN_FAILED", self.user_id, "wrong password")
            return False, "Invalid credentials"
        token = SessionStore.create(self.user_id, self.role)
        AuditLog.log(self.user_id, "LOGIN_SUCCESS", self.user_id, f"role={self.role.value}")
        return True, token

    def logout(self, token: str):
        SessionStore.revoke(token)
        AuditLog.log(self.user_id, "LOGOUT", self.user_id)

    def has_permission(self, use_case: str) -> bool:
        return use_case in ROLE_PERMISSIONS.get(self.role, [])

    def get_permissions(self) -> List[str]:
        return ROLE_PERMISSIONS.get(self.role, [])


# ── GuestAccount  (Level 1 — Guest branch) ───────────────────

class GuestAccount(UserAccount):
    """Level 1 — registered guest with online login"""
    def __init__(self, username: str, email: str, password: str, guest: "Guest"):
        super().__init__(username, email, password, UserRole.GUEST)
        self.guest    = guest          # link to Guest profile
        self.guest_id = guest.guest_id

    def get_my_reservations(self, hotel: "Hotel") -> List["Reservation"]:
        return [r for r in hotel.reservations.values()
                if r.guest.guest_id == self.guest_id]


# ── Staff  (Level 1 — Staff branch) ──────────────────────────

class Staff(UserAccount):
    """Level 1 — hotel staff base"""
    def __init__(self, username: str, email: str, password: str,
                 role: UserRole, staff_id: str, position: str):
        super().__init__(username, email, password, role)
        self.staff_id   = staff_id
        self.position   = position
        self.action_log: List[dict] = []

    def log_action(self, action: str, target: str, detail: str = ""):
        entry = AuditLog.log(self.staff_id, action, target, detail)
        self.action_log.append(entry)


# ── FrontDesk  (Level 2) ──────────────────────────────────────

class FrontDesk(Staff):
    """Level 2 — Front Desk staff"""
    def __init__(self, username: str, email: str, password: str, staff_id: str):
        super().__init__(username, email, password,
                         UserRole.FRONTDESK, staff_id, "FrontDesk")

    def process_checkin(self, reservation: "Reservation") -> bool:
        result = reservation.do_checkin(self.staff_id)
        self.log_action("CHECK_IN", reservation.reservation_id)
        return result

    def process_checkout(self, reservation: "Reservation") -> bool:
        result = reservation.do_checkout(self.staff_id)
        self.log_action("CHECK_OUT", reservation.reservation_id)
        return result

    def change_room(self, reservation: "Reservation",
                    new_room: "Room", reason: str = "") -> bool:
        """Use case: Change Room"""
        old_room = reservation.room
        old_room.release()
        new_room.allocate(reservation.reservation_id)
        reservation.room = new_room
        reservation._log(self.staff_id, "ROOM_CHANGED",
                         f"from={old_room.resource_id} to={new_room.resource_id} reason={reason}")
        self.log_action("CHANGE_ROOM", reservation.reservation_id,
                        f"{old_room.resource_id}->{new_room.resource_id}")
        return True


# ── Finance  (Level 2) ────────────────────────────────────────

class Finance(Staff):
    """Level 2 — Finance staff"""
    def __init__(self, username: str, email: str, password: str, staff_id: str):
        super().__init__(username, email, password,
                         UserRole.FINANCE, staff_id, "Finance")

    def verify_bank_transfer(self, payment: "PaymentRecord") -> bool:
        if isinstance(payment.channel, BankTransferPayment):
            payment.channel.verify(self.staff_id)
            payment.status = PaymentStatus.SUCCESS
            self.log_action("VERIFY_TRANSFER", payment.payment_id)
            return True
        return False

    def issue_refund(self, payment: "PaymentRecord") -> bool:
        payment.refund(self.staff_id)
        self.log_action("ISSUE_REFUND", payment.payment_id)
        return True

    def update_income(self, note: str, amount: float) -> dict:
        """Use case: Update Income"""
        self.log_action("UPDATE_INCOME", "income_ledger",
                        f"amount={amount:.2f} note={note}")
        return {"success": True, "recorded_by": self.staff_id,
                "amount": amount, "note": note}


# ── Manager  (Level 2) ────────────────────────────────────────

class Manager(Staff):
    """Level 2 — Hotel Manager (inherits all FrontDesk use cases via role permissions)"""
    def __init__(self, username: str, email: str, password: str, staff_id: str):
        super().__init__(username, email, password,
                         UserRole.MANAGER, staff_id, "Manager")

    def close_room_for_maintenance(self, room: "Room", reason: str) -> bool:
        room.change_state(RoomState.MAINTENANCE, self.staff_id, reason=reason)
        room.maintenance_note = reason
        self.log_action("ROOM_MAINTENANCE", room.resource_id, reason)
        return True

    def approve_exception(self, target_ref: str, reason: str) -> bool:
        self.log_action("APPROVE_EXCEPTION", target_ref, reason)
        return True


# ══════════════════════════════════════════════════════════════
#  AccountRegistry  (manages all user accounts)
# ══════════════════════════════════════════════════════════════

class AccountRegistry:
    """Singleton-style registry — lives inside Hotel"""

    def __init__(self):
        self._accounts: Dict[str, UserAccount] = {}   # username -> account
        self._by_id:    Dict[str, UserAccount] = {}   # user_id  -> account
        self._seed_staff()

    def _seed_staff(self):
        """สร้าง staff accounts ตัวอย่าง"""
        default_accounts = [
            FrontDesk("frontdesk1", "fd1@hotel.com",  "fd_pass1",  "STF-FD01"),
            FrontDesk("frontdesk2", "fd2@hotel.com",  "fd_pass2",  "STF-FD02"),
            Finance  ("finance1",   "fin1@hotel.com", "fin_pass1", "STF-FN01"),
            Finance  ("finance2",   "fin2@hotel.com", "fin_pass2", "STF-FN02"),
            Manager  ("manager1",   "mgr1@hotel.com", "mgr_pass1", "STF-MG01"),
        ]
        for acc in default_accounts:
            self._accounts[acc.username] = acc
            self._by_id[acc.user_id]     = acc

    def register_guest_account(self, username: str, email: str,
                                password: str, guest: "Guest") -> "GuestAccount":
        if username in self._accounts:
            raise ValueError(f"Username '{username}' already taken")
        acc = GuestAccount(username, email, password, guest)
        self._accounts[username] = acc
        self._by_id[acc.user_id] = acc
        AuditLog.log("system", "REGISTER_ACCOUNT", acc.user_id,
                     f"role=Guest guest_id={guest.guest_id}")
        return acc

    def get_by_username(self, username: str) -> Optional[UserAccount]:
        return self._accounts.get(username)

    def get_by_id(self, user_id: str) -> Optional[UserAccount]:
        return self._by_id.get(user_id)

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Returns (success, token_or_error)"""
        acc = self._accounts.get(username)
        if not acc:
            return False, "User not found"
        return acc.login(password)

    def get_session_info(self, token: str) -> Optional[dict]:
        return SessionStore.get(token)

    def require_permission(self, token: str, use_case: str) -> "UserAccount":
        """Validate token + permission; raise PermissionError if denied"""
        session = SessionStore.get(token)
        if not session:
            raise PermissionError("Invalid or expired token — please login again")
        acc = self._by_id.get(session["user_id"])
        if not acc:
            raise PermissionError("Account not found")
        if not acc.has_permission(use_case):
            raise PermissionError(
                f"Role '{acc.role.value}' is not allowed to perform '{use_case}'"
            )
        return acc


# ══════════════════════════════════════════════════════════════
#  Hotel  (Facade)
# ══════════════════════════════════════════════════════════════

class Hotel:
    def __init__(self):
        self.rooms:          Dict[str, Room]       = {}
        self.guests:         Dict[str, Guest]      = {}
        self.reservations:   Dict[str, Reservation] = {}
        self.invoices:       Dict[str, Invoice]    = {}
        self.extra_beds:     List[ExtraBed]        = []
        self.cleaning_tasks: List[CleaningTask]    = []
        self.notifications   = NotificationService()
        self.accounts        = AccountRegistry()     # ← NEW: auth registry
        self._seed()

    def _seed(self):
        for i in range(1, 6):
            r = Room(1, i, RoomType.STANDARD)
            self.rooms[r.resource_id] = r
        for i in range(1, 4):
            r = Room(2, i, RoomType.DELUXE)
            self.rooms[r.resource_id] = r
        for i in range(1, 6):
            self.extra_beds.append(ExtraBed(f"BED-{i:02d}"))

    # ── Guests ────────────────────────────────────────────────

    def register_guest(self, name: str, phone: str, email: str, id_doc: str = "") -> Guest:
        g = Guest(name, phone, email, id_doc)
        self.guests[g.guest_id] = g
        AuditLog.log("system", "REGISTER_GUEST", g.guest_id, name)
        return g

    def register_guest_account(self, username: str, password: str,
                                guest_id: str) -> "GuestAccount":
        """สร้าง login account ให้ Guest ที่ลงทะเบียนแล้ว"""
        guest = self.guests.get(guest_id)
        if not guest:
            raise ValueError("Guest not found")
        acc = self.accounts.register_guest_account(
            username, guest.email, password, guest)
        return acc

    # ── Room Search ───────────────────────────────────────────

    def find_available_rooms(self, room_type: RoomType,
                              check_in: datetime, check_out: datetime) -> List[Room]:
        return [
            r for r in self.rooms.values()
            if r.room_type == room_type and r.is_available()
            and not self._has_overlap(r.resource_id, check_in, check_out)
        ]

    def _has_overlap(self, room_id: str, check_in: datetime, check_out: datetime) -> bool:
        for res in self.reservations.values():
            if (res.room.resource_id == room_id
                    and res.status in (ReservationStatus.DRAFT,
                                       ReservationStatus.CONFIRMED,
                                       ReservationStatus.CHECKED_IN)):
                if check_in < res.check_out and check_out > res.check_in:
                    return True
        return False

    def _count_active_reservations(self, guest_id: str) -> int:
        cutoff = datetime.now() + timedelta(days=ACTIVE_RES_DAYS)
        return sum(
            1 for r in self.reservations.values()
            if r.guest.guest_id == guest_id
            and r.status in (ReservationStatus.DRAFT, ReservationStatus.CONFIRMED)
            and r.check_in <= cutoff
        )

    def _estimate_total(self, res: Reservation) -> float:
        rt   = res.room.price_per_night * res.nights
        disc = res.discount.apply(rt)
        ra   = rt - disc
        ex   = (PRICE["EXTRA_BED"] * res.nights) if res.extra_bed else 0.0
        vat  = math.ceil((ra + ex) * VAT_RATE)
        return ra + ex + vat

    # ── Create Reservation ────────────────────────────────────

    def create_reservation(self, guest_id: str, room_id: str,
                            check_in: datetime, check_out: datetime,
                            channel: BookingChannel = BookingChannel.WEB,
                            extra_bed: bool = False,
                            corporate_code: str = "",
                            special_requests: str = "") -> dict:
        if check_out <= check_in:
            return {"success": False, "message": "Check-out must be after check-in"}
        nights = (check_out.date() - check_in.date()).days
        if nights < 1:
            return {"success": False, "message": "Minimum 1 night required"}
        days_adv = (check_in.date() - datetime.now().date()).days
        if days_adv > MAX_ADVANCE_DAYS:
            return {"success": False, "message": f"Cannot book more than {MAX_ADVANCE_DAYS} days in advance"}
        if days_adv < 0:
            return {"success": False, "message": "Check-in date is in the past"}

        guest = self.guests.get(guest_id)
        if not guest:
            return {"success": False, "message": "Guest not found"}
        if self._count_active_reservations(guest_id) >= MAX_ACTIVE_RES:
            return {"success": False, "message": f"Max {MAX_ACTIVE_RES} active reservations per guest within {ACTIVE_RES_DAYS} days"}

        room = self.rooms.get(room_id)
        if not room:
            return {"success": False, "message": "Room not found"}
        if not room.is_available():
            return {"success": False, "message": f"Room {room_id} is not available ({room.room_state.value})"}
        if self._has_overlap(room_id, check_in, check_out):
            return {"success": False, "message": "Room already booked for this period"}
        if extra_bed and not any(b.is_available() for b in self.extra_beds):
            return {"success": False, "message": "No extra beds available"}

        res = Reservation(guest, room, check_in, check_out, channel,
                          extra_bed, corporate_code, special_requests)
        room.allocate(res.reservation_id)
        self.reservations[res.reservation_id] = res

        if extra_bed:
            bed = next(b for b in self.extra_beds if b.is_available())
            bed.allocate(res.reservation_id)
            res.extra_bed_res = bed

        AuditLog.log("system", "CREATE_RESERVATION", res.reservation_id,
                     f"guest={guest_id}, room={room_id}")
        return {
            "success":           True,
            "reservation_id":    res.reservation_id,
            "room_id":           room_id,
            "room_type":         room.room_type.value,
            "nights":            nights,
            "channel":           channel.value,
            "hold_expires_at":   res.hold_expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "discount_type":     res.discount.discount_type.value,
            "discount_rate_pct": int(res.discount.rate * 100),
            "deposit_required":  res.deposit_amount,
            "estimated_total":   self._estimate_total(res),
        }

    # ── Confirm Reservation ───────────────────────────────────

    def confirm_reservation(self, reservation_id: str,
                             payment_channel: AbstractPaymentChannel) -> dict:
        res = self.reservations.get(reservation_id)
        if not res:
            return {"success": False, "message": "Reservation not found"}
        if res.is_hold_expired:
            res.status = ReservationStatus.CANCELLED
            res.room.release()
            return {"success": False, "message": "Hold expired — reservation auto-cancelled"}
        if res.status != ReservationStatus.DRAFT:
            return {"success": False, "message": f"Cannot confirm: status is {res.status.value}"}

        inv = Invoice(res)
        res.invoice = inv
        self.invoices[reservation_id] = inv

        pay = PaymentRecord(reservation_id, res.deposit_amount,
                            PaymentType.DEPOSIT, payment_channel)
        if not pay.execute():
            res.room.release()
            res.status = ReservationStatus.CANCELLED
            inv.void()
            return {"success": False, "message": "Deposit payment failed — reservation cancelled"}

        inv.payments.append(pay)
        inv.update_status()
        res.confirm(pay)

        self.notifications.notify(
            res.guest.email, NotificationEvent.BOOKING_CONFIRMED,
            {"message": f"Reservation {reservation_id} confirmed! Check-in: {res.check_in.date()}"},
            channels=["Email", "InApp"]
        )
        AuditLog.log("system", "CONFIRM_RESERVATION", reservation_id)
        return {
            "success":        True,
            "reservation_id": reservation_id,
            "invoice_no":     inv.invoice_no,
            "deposit_paid":   res.deposit_amount,
            "balance_due":    inv.balance_due(),
            "invoice":        inv.to_dict(),
        }

    # ── Pay Balance ───────────────────────────────────────────

    def pay_balance(self, reservation_id: str,
                    payment_channel: AbstractPaymentChannel) -> dict:
        res = self.reservations.get(reservation_id)
        if not res or not res.invoice:
            return {"success": False, "message": "Reservation or invoice not found"}
        if res.status not in (ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN):
            return {"success": False, "message": f"Cannot pay: status is {res.status.value}"}
        balance = res.invoice.balance_due()
        if balance <= 0:
            return {"success": False, "message": "No outstanding balance"}

        pay = PaymentRecord(reservation_id, balance, PaymentType.BALANCE, payment_channel)
        if not pay.execute():
            return {"success": False, "message": "Payment failed"}

        res.invoice.payments.append(pay)
        res.invoice.update_status()
        res.payments.append(pay)
        AuditLog.log("system", "PAY_BALANCE", reservation_id, f"amount={balance:.2f}")
        return {
            "success":        True,
            "payment_id":     pay.payment_id,
            "amount_paid":    balance,
            "invoice_status": res.invoice.status,
        }

    # ── Cancel Reservation ────────────────────────────────────

    def cancel_reservation(self, reservation_id: str, actor: str = "system") -> dict:
        res = self.reservations.get(reservation_id)
        if not res:
            return {"success": False, "message": "Reservation not found"}
        if res.status == ReservationStatus.CANCELLED:
            return {"success": False, "message": "Already cancelled"}
        if res.status not in (ReservationStatus.DRAFT, ReservationStatus.CONFIRMED):
            return {"success": False, "message": f"Cannot cancel: status is {res.status.value}"}

        penalty, refund = res.cancel(actor)
        res.room.release()
        if res.invoice:
            if penalty > 0:
                res.invoice.add_penalty(penalty)
            else:
                res.invoice.void()

        AuditLog.log(actor, "CANCEL_RESERVATION", reservation_id,
                     f"penalty={penalty}, refund={refund}")
        return {
            "success":           True,
            "reservation_id":    reservation_id,
            "cancellation_type": "free" if penalty == 0 else "with_penalty",
            "penalty":           penalty,
            "refund":            refund,
            "message": ("Cancelled — full refund" if penalty == 0
                        else f"Cancelled — penalty {penalty:.2f} THB (first-night rate)"),
        }

    # ── Check-In ──────────────────────────────────────────────

    def check_in(self, reservation_id: str, actor: str = "FrontDesk") -> dict:
        res = self.reservations.get(reservation_id)
        if not res:
            return {"success": False, "message": "Reservation not found"}
        if res.status != ReservationStatus.CONFIRMED:
            return {"success": False, "message": f"Cannot check-in: status is {res.status.value}"}
        if not res.do_checkin(actor):
            return {"success": False, "message": "Check-in failed"}

        AuditLog.log(actor, "CHECK_IN", reservation_id)
        return {
            "success":        True,
            "reservation_id": reservation_id,
            "room_id":        res.room.resource_id,
            "guest":          res.guest.name,
            "check_in":       res.check_in.strftime("%Y-%m-%d %H:%M"),
            "check_out":      res.check_out.strftime("%Y-%m-%d %H:%M"),
            "balance_due":    res.invoice.balance_due() if res.invoice else 0,
        }

    # ── Check-Out ─────────────────────────────────────────────

    def check_out(self, reservation_id: str, actor: str = "FrontDesk") -> dict:
        res = self.reservations.get(reservation_id)
        if not res:
            return {"success": False, "message": "Reservation not found"}
        if res.status != ReservationStatus.CHECKED_IN:
            return {"success": False, "message": f"Cannot check-out: status is {res.status.value}"}
        if res.invoice and res.invoice.balance_due() > 0:
            return {"success": False, "message": "Outstanding balance — please pay before checkout",
                    "balance_due": res.invoice.balance_due()}

        if not res.do_checkout(actor):
            return {"success": False, "message": "Check-out failed"}

        task_id = f"CLN-{res.room.resource_id}-{datetime.now().strftime('%Y%m%d%H%M')}"
        task = CleaningTask(task_id, res.room.resource_id)
        self.cleaning_tasks.append(task)

        self.notifications.notify(
            res.guest.email, NotificationEvent.CHECKOUT_SUMMARY,
            {"message": f"Thank you {res.guest.name}! Invoice: {res.invoice.invoice_no if res.invoice else '-'}"},
            channels=["Email", "InApp"]
        )
        AuditLog.log(actor, "CHECK_OUT", reservation_id)
        return {
            "success":          True,
            "reservation_id":   reservation_id,
            "room_id":          res.room.resource_id,
            "cleaning_task_id": task_id,
            "invoice":          res.invoice.to_dict() if res.invoice else None,
        }

    # ── No-Show ───────────────────────────────────────────────

    def mark_no_show(self, reservation_id: str, actor: str = "system") -> dict:
        res = self.reservations.get(reservation_id)
        if not res:
            return {"success": False, "message": "Reservation not found"}
        if res.status != ReservationStatus.CONFIRMED:
            return {"success": False, "message": f"Cannot mark no-show: status is {res.status.value}"}

        cutoff = res.check_in.replace(hour=NOSHOW_CUTOFF_HOUR, minute=0, second=0)
        if datetime.now() < cutoff:
            return {"success": False,
                    "message": f"Cannot mark no-show before {NOSHOW_CUTOFF_HOUR}:00 on check-in day"}

        penalty = res.mark_no_show(actor)
        if res.invoice:
            res.invoice.add_penalty(penalty)

        self.notifications.notify(
            res.guest.email, NotificationEvent.NO_SHOW,
            {"message": f"No-show recorded. Penalty: {penalty:.2f} THB"},
            channels=["Email"]
        )
        AuditLog.log(actor, "NO_SHOW", reservation_id, f"penalty={penalty}")
        return {
            "success":               True,
            "reservation_id":        reservation_id,
            "penalty":               penalty,
            "guest_noshow_count":    res.guest.recent_no_show_count(),
            "next_deposit_required": res.guest.required_deposit(),
        }

    # ── Cleaning Complete ─────────────────────────────────────

    def complete_cleaning(self, room_id: str, worker_id: str = "housekeeping") -> dict:
        room = self.rooms.get(room_id)
        if not room:
            return {"success": False, "message": "Room not found"}
        task = next((t for t in self.cleaning_tasks
                     if t.room_id == room_id and t.completed_at is None), None)
        if task:
            task.complete(worker_id)
        room.change_state(RoomState.AVAILABLE, worker_id, reason="cleaning complete")
        AuditLog.log(worker_id, "CLEANING_COMPLETE", room_id)
        return {"success": True, "room_id": room_id, "status": "Available"}

    # ── Reports ───────────────────────────────────────────────

    def report_daily_occupancy(self) -> dict:
        counts = {s: 0 for s in RoomState}
        for r in self.rooms.values():
            counts[r.room_state] += 1
        return {
            "date":        datetime.now().strftime("%Y-%m-%d"),
            "total_rooms": len(self.rooms),
            "available":   counts[RoomState.AVAILABLE],
            "hold":        counts[RoomState.HOLD],
            "occupied":    counts[RoomState.OCCUPIED],
            "cleaning":    counts[RoomState.CLEANING],
            "maintenance": counts[RoomState.MAINTENANCE],
        }

    def report_monthly_revenue(self, year: int, month: int) -> dict:
        ri = ei = vi = pi = 0.0
        for res in self.reservations.values():
            if (res.status == ReservationStatus.CHECKED_OUT
                    and res.check_out.year == year
                    and res.check_out.month == month
                    and res.invoice):
                inv = res.invoice
                ri += inv.room_after_disc
                ei += inv.extra_bed_subtotal
                vi += inv.vat_amount
                pi += inv.penalty_amount
        return {"year": year, "month": month,
                "room_income": ri, "extra_bed_income": ei,
                "vat_collected": vi, "penalty_income": pi, "total": ri+ei+vi+pi}

    def report_cancellations(self, year: int, quarter: int) -> dict:
        sm = (quarter - 1) * 3 + 1
        em = sm + 2
        cancelled = no_shows = 0
        penalty_total = 0.0
        for res in self.reservations.values():
            if res.booking_date.year == year and sm <= res.booking_date.month <= em:
                if res.status == ReservationStatus.CANCELLED:
                    cancelled += 1
                    penalty_total += res.penalty_amount
                elif res.status == ReservationStatus.NO_SHOW:
                    no_shows += 1
                    penalty_total += res.penalty_amount
        return {"year": year, "quarter": quarter,
                "cancellations": cancelled, "no_shows": no_shows,
                "total_penalty_collected": penalty_total}