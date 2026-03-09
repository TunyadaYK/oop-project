# roomstatus_diagram.py
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from typing import Optional, Dict

app = FastAPI()

# ---------------------------
# Enum: RoomState
# ---------------------------
class RoomState(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    OCCUPIED = "Occupied"
    MAINTENANCE = "Maintenance"


# ---------------------------
# Class: RoomStatus
# (ตรงกับ diagram: name + checkAvailability + toString)
# ---------------------------
class RoomStatus:
    def __init__(self, name: RoomState):
        self.name: RoomState = name

    def checkAvailability(self, startDate: str, endDate: str) -> bool:
        # ตาม logic โค้ดเดิมของคุณ: ว่างจริงเฉพาะ Available
        return self.name == RoomState.AVAILABLE

    def __str__(self) -> str:
        # เทียบกับ toString() ใน diagram
        return self.name.value


# ---------------------------
# Class: Room
# (ตรงกับ diagram: room_id, status, status_updated_at, status_time, updateStatus, isAvailableNow)
# ---------------------------
class Room:
    def __init__(self, room_id: str):
        self.room_id: str = room_id

        now = datetime.now().replace(microsecond=0)

        self.status: RoomStatus = RoomStatus(RoomState.AVAILABLE)
        self.status_updated_at: datetime = now

        # Map<RoomState, DateTime?>
        self.status_time: Dict[RoomState, Optional[datetime]] = {s: None for s in RoomState}
        self.status_time[self.status.name] = now

    def updateStatus(self, newStatus: RoomStatus) -> bool:
        now = datetime.now().replace(microsecond=0)

        self.status = newStatus
        self.status_updated_at = now
        self.status_time[newStatus.name] = now

        print(f"Room {self.room_id} -> {newStatus.name.value} @ {now}")
        return True

    def isAvailableNow(self) -> bool:
        return self.status.name == RoomState.AVAILABLE


# ---------------------------
# Demo data (ห้อง 2 ห้อง)
# ---------------------------
rooms: Dict[str, Room] = {
    "101": Room("101"),
    "102": Room("102"),
}


# ---------------------------
# FastAPI (เหมือนของเดิม แต่ใช้โครง diagram)
# ---------------------------
class RoomStatusUpdateRequest(BaseModel):
    new_status: RoomState


@app.post("/room_status/{room_id}")
def update_room_status(room_id: str, request: RoomStatusUpdateRequest):
    if room_id not in rooms:
        return {"error": "Room not found"}

    room = rooms[room_id]
    room.updateStatus(RoomStatus(request.new_status))

    return {
        "message": f"Room {room_id} status updated to {room.status.name.value}",
        "status": room.status.name.value,
        "updated_at": room.status_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status_time": {
            state.value: (t.strftime("%Y-%m-%d %H:%M:%S") if t else None)
            for state, t in room.status_time.items()
        },
        "is_available_now": room.isAvailableNow(),
    }


# ---------------------------
# Simple test (รันไฟล์ตรง ๆ ก็เห็น log)
# ---------------------------
if __name__ == "__main__":
    print("=== Local Test ===")
    rooms["101"].updateStatus(RoomStatus(RoomState.RESERVED))
    rooms["101"].updateStatus(RoomStatus(RoomState.OCCUPIED))
    rooms["101"].updateStatus(RoomStatus(RoomState.AVAILABLE))
    rooms["101"].updateStatus(RoomStatus(RoomState.MAINTENANCE))
    print("Current status:", str(rooms["101"].status))