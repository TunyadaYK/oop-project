from datetime import datetime
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Hotel Check-In API")


class Reservation:
    def __init__(self, reservation_id, guest_name, room_id, status="Reserved"):
        self.reservation_id = reservation_id
        self.guest_name = guest_name
        self.room_id = room_id
        self.status = status

    def validateForCheckIn(self):
        return self.status == "Reserved"


class Room:
    def __init__(self, room_id, status="Available"):
        self.room_id = room_id
        self.status = status

    def changeStatus(self, new_status):
        self.status = new_status


class StayRecord:
    def __init__(self, record_id, guest_name, room_id, checkin_time):
        self.record_id = record_id
        self.guest_name = guest_name
        self.room_id = room_id
        self.checkin_time = checkin_time

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "guest_name": self.guest_name,
            "room_id": self.room_id,
            "checkin_time": self.checkin_time
        }

    def __str__(self):
        return (
            f"StayRecord(record_id={self.record_id}, "
            f"guest_name='{self.guest_name}', "
            f"room_id='{self.room_id}', "
            f"checkin_time='{self.checkin_time}')"
        )


class ReservationDB:
    def __init__(self):
        self.reservations = {}

    def add_reservation(self, reservation):
        self.reservations[reservation.reservation_id] = reservation

    def find_reservation(self, reservation_id):
        return self.reservations.get(reservation_id)


class RoomDB:
    def __init__(self):
        self.rooms = {}

    def add_room(self, room):
        self.rooms[room.room_id] = room

    def find_room(self, room_id):
        return self.rooms.get(room_id)


class StayRecordDB:
    def __init__(self):
        self.records = {}
        self.next_id = 1

    def save_record(self, guest_name, room_id):
        record = StayRecord(
            record_id=self.next_id,
            guest_name=guest_name,
            room_id=room_id,
            checkin_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.records[self.next_id] = record
        self.next_id += 1
        return record


class ReservationService:
    def __init__(self, reservation_db):
        self.reservation_db = reservation_db

    def checkReservation(self, reservation_id):
        reservation = self.reservation_db.find_reservation(reservation_id)
        if reservation and reservation.validateForCheckIn():
            return reservation
        return None

    def confirmCheckIn(self, reservation):
        reservation.status = "Checked-In"


class RoomService:
    def __init__(self, room_db):
        self.room_db = room_db

    def changeRoomStatus(self, room_id, new_status):
        room = self.room_db.find_room(room_id)
        if room:
            room.changeStatus(new_status)
            return room
        return None


class StayRecordService:
    def __init__(self, stay_record_db):
        self.stay_record_db = stay_record_db

    def createStayRecord(self, guest_name, room_id):
        return self.stay_record_db.save_record(guest_name, room_id)


class HotelSystem:
    def __init__(self):
        self.reservation_db = ReservationDB()
        self.room_db = RoomDB()
        self.stay_record_db = StayRecordDB()

        self.reservation_service = ReservationService(self.reservation_db)
        self.room_service = RoomService(self.room_db)
        self.stay_record_service = StayRecordService(self.stay_record_db)

    def checkIn(self, reservation_id):
        reservation = self.reservation_service.checkReservation(reservation_id)
        if not reservation:
            return {
                "success": False,
                "message": "Check-In failed: Reservation not found or invalid"
            }

        self.reservation_service.confirmCheckIn(reservation)

        room = self.room_service.changeRoomStatus(reservation.room_id, "Occupied")
        if not room:
            return {
                "success": False,
                "message": "Check-In failed: Room not found"
            }

        stay_record = self.stay_record_service.createStayRecord(
            reservation.guest_name,
            reservation.room_id
        )

        return {
            "success": True,
            "message": "Check-In successful",
            "reservation_id": reservation.reservation_id,
            "guest_name": reservation.guest_name,
            "room_id": reservation.room_id,
            "reservation_status": reservation.status,
            "room_status": room.status,
            "stay_record": stay_record.to_dict()
        }


hotel = HotelSystem()

hotel.room_db.add_room(Room("A101"))
hotel.room_db.add_room(Room("A102"))

hotel.reservation_db.add_reservation(Reservation("R001", "Alice", "A101"))
hotel.reservation_db.add_reservation(Reservation("R002", "Bob", "A102", status="Cancelled"))


@app.get("/")
def home():
    return {
        "message": "Hotel Check-In API is running",
        "docs": "/docs"
    }


@app.get("/reservations")
def get_reservations():
    data = []
    for reservation in hotel.reservation_db.reservations.values():
        data.append({
            "reservation_id": reservation.reservation_id,
            "guest_name": reservation.guest_name,
            "room_id": reservation.room_id,
            "status": reservation.status
        })
    return data


@app.get("/rooms")
def get_rooms():
    data = []
    for room in hotel.room_db.rooms.values():
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


@app.get("/stay-records")
def get_stay_records():
    data = []
    for record in hotel.stay_record_db.records.values():
        data.append(record.to_dict())
    return data