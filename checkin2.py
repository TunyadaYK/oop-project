from datetime import datetime
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Hotel Check-In API")


class Room:
    def __init__(self, room_id, status="Available"):
        self.room_id = room_id
        self.status = status

    def changeStatus(self, new_status):
        self.status = new_status


class Invoice:
    def __init__(self, invoice_no, status="Valid"):
        self.invoiceNo = invoice_no
        self.status = status

    def validate(self):
        return self.status == "Valid"


class Reservation:
    def __init__(self, reservation_id, guest_name, room_id, status="Reserved", invoice=None):
        self.reservation_id = reservation_id
        self.guest_name = guest_name
        self.room_id = room_id
        self.status = status
        self.invoice = invoice
        self.checkInDate = None
        self.checkOutDate = None

    def validateForCheckIn(self):
        return self.status == "Reserved"


class AuditLog:
    def __init__(self):
        self.logs = []

    def logAuditAction(self, actorId, action, targetRef):
        log = {
            "actorId": actorId,
            "action": action,
            "targetRef": targetRef,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.logs.append(log)
        return log


class Hotel:
    def __init__(self):
        self.rooms = {}
        self.reservations = {}
        self.auditLog = AuditLog()

    def checkIn(self, bookingId):
        reservation = self.reservations.get(bookingId)
        if not reservation or not reservation.validateForCheckIn():
            return {
                "success": False,
                "message": "Check-In failed: Reservation not found or invalid"
            }

        if reservation.invoice and not reservation.invoice.validate():
            return {
                "success": False,
                "message": "Check-In failed: Invoice invalid"
            }

        room = self.rooms.get(reservation.room_id)
        if not room:
            return {
                "success": False,
                "message": "Check-In failed: Room not found"
            }

        reservation.status = "Checked-In"
        reservation.checkInDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        room.changeStatus("Occupied")

        audit = self.auditLog.logAuditAction("FrontDesk", "Check-In", bookingId)

        return {
            "success": True,
            "message": "Check-In successful",
            "reservation_id": reservation.reservation_id,
            "guest_name": reservation.guest_name,
            "room_id": reservation.room_id,
            "reservation_status": reservation.status,
            "checkInDate": reservation.checkInDate,
            "checkOutDate": reservation.checkOutDate,
            "room_status": room.status,
            "audit_log": audit
        }


hotel = Hotel()

hotel.rooms["A101"] = Room("A101")
hotel.rooms["A102"] = Room("A102")

hotel.reservations["R001"] = Reservation(
    "R001", "Alice", "A101", "Reserved", Invoice("INV001", "Valid")
)
hotel.reservations["R002"] = Reservation(
    "R002", "Bob", "A102", "Cancelled", Invoice("INV002", "Valid")
)


@app.get("/")
def home():
    return {
        "message": "Hotel Check-In API is running",
        "docs": "/docs"
    }


@app.get("/reservations")
def get_reservations():
    data = []
    for reservation in hotel.reservations.values():
        data.append({
            "reservation_id": reservation.reservation_id,
            "guest_name": reservation.guest_name,
            "room_id": reservation.room_id,
            "status": reservation.status,
            "invoice_no": reservation.invoice.invoiceNo if reservation.invoice else None,
            "checkInDate": reservation.checkInDate,
            "checkOutDate": reservation.checkOutDate
        })
    return data


@app.get("/rooms")
def get_rooms():
    data = []
    for room in hotel.rooms.values():
        data.append({
            "room_id": room.room_id,
            "status": room.status
        })
    return data


@app.post("/checkin/{reservation_id}")
def check_in_api(reservation_id: str):
    result = hotel.checkIn(reservation_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/audit-logs")
def get_audit_logs():
    return hotel.auditLog.logs