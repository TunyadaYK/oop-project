from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, date, time
import uvicorn

from models import Hotel

app = FastAPI(title="Hotel Reservation API")

hotel_system = Hotel()


class ReservationRequest(BaseModel):
    guestName: str
    roomType: str
    checkIn: date
    checkOut: date
    discount: float = 0


class ReservationResponse(BaseModel):
    status: str
    reservationNo: str
    roomNumber: int
    totalAmount: float



@app.post("/reservations", response_model=ReservationResponse)
def create_reservation(req: ReservationRequest):

    check_in_dt = datetime.combine(req.checkIn, time.min)
    check_out_dt = datetime.combine(req.checkOut, time.min)

    result = hotel_system.createReservation(
        req.guestName,
        req.roomType,
        check_in_dt,
        check_out_dt,
        req.discount
    )
    if req.checkOut <= req.checkIn:
        raise HTTPException(status_code=400, detail="Invalid date range")

    if result.status == "fail":
        raise HTTPException(status_code=400, detail="No room available")

    return ReservationResponse(
        status=result.status,
        reservationNo=result.reservation_no,
        roomNumber=result.room_number,
        totalAmount=result.total_amount
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
