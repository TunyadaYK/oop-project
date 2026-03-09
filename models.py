from datetime import datetime
from typing import List, Optional


class Room:
    def __init__(self, room_number: int, room_type: str):
        self.room_number = room_number
        self.room_type = room_type
        self.status = "Available"

    def isAvailable(self, check_in: datetime, check_out: datetime,
                    reservations: List["Reservation"]) -> bool:

        for r in reservations:
            if r.room == self:
                if check_in < r.check_out and check_out > r.check_in:
                    return False
        return True

    def changeStatus(self, new_status: str):
        self.status = new_status
        return True


class Reservation:
    def __init__(self, reservation_no: str,
                 guest_name: str,
                 room: Room,
                 check_in: datetime,
                 check_out: datetime):

        self.reservation_no = reservation_no
        self.guest_name = guest_name
        self.room = room
        self.check_in = check_in
        self.check_out = check_out
        self.total_amount = 0
        self.status = "Active"

    def calculateTotal(self):
        nights = (self.check_out - self.check_in).days
        price_per_night = 1000 if self.room.room_type == "STANDARD" else 2000
        self.total_amount = nights * price_per_night

    def applyDiscount(self, discount_percent: float):
        discount_value = self.total_amount * (discount_percent / 100)
        self.total_amount -= discount_value

    def cancelBooking(self):
        self.status = "Cancelled"


class Invoice:
    running_no = 1

    def __init__(self, reservation: Reservation):
        self.invoice_no = f"INV{Invoice.running_no:04d}"
        Invoice.running_no += 1
        self.reservation = reservation
        self.status = "Unpaid"

    def updateStatus(self, amount_paid: float):
        if amount_paid >= self.reservation.total_amount:
            self.status = "Paid"

    def voidInvoice(self):
        self.status = "Voided"


class Payment:
    def __init__(self, amount: float):
        self.amount = amount

    def processPayment(self) -> bool:
        return True


class ReservationResult:
    def __init__(self, status: str,
                 reservation_no: Optional[str] = None,
                 room_number: Optional[int] = None,
                 total_amount: Optional[float] = None,
                 message: Optional[str] = None):
        self.status = status
        self.reservation_no = reservation_no
        self.room_number = room_number
        self.total_amount = total_amount


class Hotel:
    def __init__(self):
        self.rooms: List[Room] = []
        self.reservations: List[Reservation] = []
        self.running_no = 1

        for i in range(1, 6):
            self.rooms.append(Room(i, "STANDARD"))

        for i in range(6, 9):
            self.rooms.append(Room(i, "DELUXE"))

    def generateReservationNo(self) -> str:
        res_no = f"RES{self.running_no:04d}"
        self.running_no += 1
        return res_no

    def findAvailableRoom(self, room_type: str,
                          check_in: datetime,
                          check_out: datetime) -> Optional[Room]:

        for room in self.rooms:
            if room.room_type == room_type:
                if room.isAvailable(check_in, check_out, self.reservations):
                    return room
        return None

    def createReservation(self,
                          guest_name: str,
                          room_type: str,
                          check_in: datetime,
                          check_out: datetime,
                          discount: float = 0) -> ReservationResult:

        if check_out <= check_in:
            return ReservationResult("fail", message="Invalid date range")

        room = self.findAvailableRoom(room_type, check_in, check_out)

        if not room:
            return ReservationResult("fail", message="No room available")

        # กันจองซ้อน
        room.changeStatus("Locked/Pending")

        # Create Reservation
        reservation_no = self.generateReservationNo()
        reservation = Reservation(
            reservation_no,
            guest_name,
            room,
            check_in,
            check_out
        )

        reservation.calculateTotal()

        if discount > 0:
            reservation.applyDiscount(discount)

        self.reservations.append(reservation)

        # Create Invoice
        invoice = Invoice(reservation)

        # Payment 
        payment = Payment(reservation.total_amount)
        is_payment_success = payment.processPayment()

        if not is_payment_success:
            # Parment fail
            reservation.cancelBooking()
            invoice.voidInvoice()
            room.changeStatus("Available")
            
            return ReservationResult("fail", message="Payment failed")

        # Payment Success 
        invoice.updateStatus(reservation.total_amount)
        room.changeStatus("Reserved")

        return ReservationResult(
            "success",
            reservation_no=reservation.reservation_no,
            room_number=room.room_number,
            total_amount=reservation.total_amount
        )
