
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from livekit import api as livekit_api

from .database import Base, engine, get_db
from .models import Stylist, Service, Booking
from .schemas import BookingCreate, RescheduleRequest, CancelRequest
from .seed import seed


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

TZ = ZoneInfo("Asia/Kolkata")

app = FastAPI(
    title="Sunrise Salon Voice Agent API",
    version="1.0.0",
    description="Backend API for Sunrise Salon AI Voice Receptionist"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# DATABASE STARTUP
# --------------------------------------------------

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    from .database import SessionLocal

    db = SessionLocal()

    try:
        seed(db)
    finally:
        db.close()


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Sunrise Salon API"
    }


# --------------------------------------------------
# BUSINESS INFORMATION
# --------------------------------------------------

@app.get("/api/business")
def business():
    return {
        "name": "Sunrise Salon",
        "address": "12 Lake Road, Indiranagar, Bengaluru",
        "timezone": "Asia/Kolkata",
        "slot_minutes": 30,
        "closed": ["Sunday"],

        "cancellation_policy":
            "Free cancellation up to 2 hours before the appointment.",

        "faqs": {
            "payment": "Cash, UPI and cards.",
            "walk_ins":
                "Walk-ins are welcome; booked customers are served first.",
            "parking": "Street parking only.",
            "late_arrival":
                "More than 15 minutes late, the booking may be moved to the next free slot.",
            "discounts": "No discounts right now.",
            "membership":
                "No membership or package information on file."
        },

        "not_offered": [
            "nail art",
            "waxing",
            "makeup",
            "tattoos",
            "home service"
        ]
    }


# --------------------------------------------------
# SERVICES
# --------------------------------------------------

@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [
        {
            "id": service.id,
            "name": service.name,
            "price": service.price_text,
            "stylist": service.stylist.name
        }
        for service in db.query(Service).all()
    ]


# --------------------------------------------------
# AVAILABLE APPOINTMENT SLOTS
# --------------------------------------------------

def slots_for(service: Service, day: date, db: Session):
    stylist = service.stylist

    weekday = day.strftime("%a")

    if weekday not in stylist.weekdays.split(","):
        return []

    result = []

    current = datetime.combine(
        day,
        time(stylist.start_hour),
        TZ
    )

    end = datetime.combine(
        day,
        time(stylist.end_hour),
        TZ
    )

    while current + timedelta(minutes=30) <= end:

        occupied = db.query(Booking).filter(
            Booking.stylist_id == stylist.id,
            Booking.starts_at == current,
            Booking.status == "booked"
        ).first()

        if not occupied:
            result.append(current.isoformat())

        current += timedelta(minutes=30)

    return result


@app.get("/api/availability")
def availability(
    service_id: int,
    date: date,
    db: Session = Depends(get_db)
):
    service = db.get(Service, service_id)

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    return {
        "service": service.name,
        "stylist": service.stylist.name,
        "date": date.isoformat(),
        "available_slots": slots_for(service, date, db)
    }


# --------------------------------------------------
# CREATE BOOKING
# --------------------------------------------------

@app.post("/api/bookings")
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db)
):
    service = db.get(Service, payload.service_id)

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    start = payload.starts_at.astimezone(TZ)

    if (
        start.minute not in (0, 30)
        or start.second
        or start.microsecond
    ):
        raise HTTPException(
            status_code=400,
            detail="Appointments must start on a 30-minute boundary."
        )

    available_slots = [
        datetime.fromisoformat(slot)
        for slot in slots_for(service, start.date(), db)
    ]

    if start not in available_slots:
        raise HTTPException(
            status_code=409,
            detail="That slot is not available. Please choose another."
        )

    booking = Booking(
        stylist_id=service.stylist_id,
        service_id=service.id,
        starts_at=start,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        status="booked",
        created_at=datetime.now(TZ)
    )

    db.add(booking)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="That slot was just booked by someone else. Please choose another."
        )

    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "service": service.name,
        "stylist": service.stylist.name,
        "starts_at": booking.starts_at.isoformat(),
        "status": booking.status
    }


# --------------------------------------------------
# RESCHEDULE BOOKING
# --------------------------------------------------

@app.patch("/api/bookings/{booking_id}/reschedule")
def reschedule(
    booking_id: int,
    payload: RescheduleRequest,
    db: Session = Depends(get_db)
):
    booking = db.get(Booking, booking_id)

    if not booking or booking.status != "booked":
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    start = payload.starts_at.astimezone(TZ)

    service = db.get(Service, booking.service_id)

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    if (
        start.minute not in (0, 30)
        or start.second
        or start.microsecond
    ):
        raise HTTPException(
            status_code=400,
            detail="Appointments must start on a 30-minute boundary."
        )

    available_slots = [
        datetime.fromisoformat(slot)
        for slot in slots_for(service, start.date(), db)
    ]

    if start not in available_slots:
        raise HTTPException(
            status_code=409,
            detail="That slot is not available."
        )

    booking.starts_at = start

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="That slot was just booked. Please choose another."
        )

    return {
        "booking_id": booking.id,
        "starts_at": start.isoformat(),
        "status": "rescheduled"
    }


# --------------------------------------------------
# CANCEL BOOKING
# --------------------------------------------------

@app.post("/api/bookings/{booking_id}/cancel")
def cancel(
    booking_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db)
):
    booking = db.get(Booking, booking_id)

    if (
        not booking
        or booking.status != "booked"
        or booking.customer_phone != payload.phone
    ):
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    now = datetime.now(TZ)
    starts = booking.starts_at.astimezone(TZ)

    free = now <= starts - timedelta(hours=2)

    booking.status = "cancelled"

    db.commit()

    return {
        "booking_id": booking.id,
        "status": "cancelled",
        "free_cancellation": free,
        "message": (
            "Cancelled free of charge."
            if free
            else "Cancelled; this is less than 2 hours before the appointment, so it is not free."
        )
    }


# --------------------------------------------------
# BOOKING SERIALIZER FOR DASHBOARDS
# --------------------------------------------------

def booking_to_dict(booking: Booking, db: Session):
    service = db.get(Service, booking.service_id)
    stylist = db.get(Stylist, booking.stylist_id)

    return {
        "id": booking.id,
        "customer_name": booking.customer_name,
        "customer_phone": booking.customer_phone,

        "service": (
            service.name if service else "Unknown service"
        ),

        "stylist": (
            stylist.name if stylist else "Unassigned"
        ),

        "starts_at": booking.starts_at.isoformat(),

        "status": booking.status,

        "created_at": (
            booking.created_at.isoformat()
            if booking.created_at
            else None
        )
    }


# --------------------------------------------------
# CUSTOMER DASHBOARD
# --------------------------------------------------

@app.get("/api/customer/bookings")
def customer_bookings(
    phone: str,
    db: Session = Depends(get_db)
):
    if not phone.strip():
        raise HTTPException(
            status_code=400,
            detail="Phone number is required."
        )

    bookings = (
        db.query(Booking)
        .filter(Booking.customer_phone == phone.strip())
        .order_by(Booking.starts_at.desc())
        .all()
    )

    return {
        "total": len(bookings),
        "bookings": [
            booking_to_dict(booking, db)
            for booking in bookings
        ]
    }


# --------------------------------------------------
# STAFF AUTHENTICATION
# --------------------------------------------------

def verify_staff(
    x_staff_password: str = Header(default="")
):
    expected_password = os.getenv("STAFF_PASSWORD")

    if not expected_password:
        raise HTTPException(
            status_code=503,
            detail="Staff password is not configured on the server."
        )

    if x_staff_password != expected_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid staff password."
        )

    return True


# --------------------------------------------------
# STAFF DASHBOARD - VIEW ALL BOOKINGS
# --------------------------------------------------

@app.get("/api/staff/bookings")
def staff_bookings(
    authenticated: bool = Depends(verify_staff),
    db: Session = Depends(get_db)
):
    bookings = (
        db.query(Booking)
        .order_by(Booking.starts_at.desc())
        .all()
    )

    return {
        "total": len(bookings),
        "bookings": [
            booking_to_dict(booking, db)
            for booking in bookings
        ]
    }


# --------------------------------------------------
# STAFF DASHBOARD - MARK BOOKING COMPLETED
# --------------------------------------------------

@app.patch("/api/staff/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    authenticated: bool = Depends(verify_staff),
    db: Session = Depends(get_db)
):
    booking = db.get(Booking, booking_id)

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found."
        )

    if booking.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="Only booked appointments can be marked completed."
        )

    booking.status = "completed"

    db.commit()
    db.refresh(booking)

    return {
        "message": "Appointment marked as completed.",
        "booking": booking_to_dict(booking, db)
    }


# --------------------------------------------------
# STAFF DASHBOARD - DELETE COMPLETED BOOKING
# --------------------------------------------------

@app.delete("/api/staff/bookings/{booking_id}")
def delete_booking(
    booking_id: int,
    authenticated: bool = Depends(verify_staff),
    db: Session = Depends(get_db)
):
    booking = db.get(Booking, booking_id)

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found."
        )

    if booking.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed bookings can be deleted."
        )

    db.delete(booking)
    db.commit()

    return {
        "message": "Completed booking deleted successfully.",
        "booking_id": booking_id
    }


# --------------------------------------------------
# LIVEKIT VOICE CALL TOKEN
# --------------------------------------------------

@app.post("/api/livekit/token")
def livekit_token():

    required_keys = (
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "LIVEKIT_URL"
    )

    if not all(os.getenv(key) for key in required_keys):
        raise HTTPException(
            status_code=503,
            detail="LiveKit credentials are not configured."
        )

    token = livekit_api.AccessToken(
        os.environ["LIVEKIT_API_KEY"],
        os.environ["LIVEKIT_API_SECRET"]
    )

    room_name = os.getenv(
        "LIVEKIT_ROOM",
        "sunrise-salon"
    )

    token.with_identity(
        f"web-caller-{uuid4().hex[:8]}"
    ).with_name(
        "Sunrise Salon caller"
    ).with_grants(
        livekit_api.VideoGrants(
            room_join=True,
            room=room_name
        )
    ).with_room_config(
        livekit_api.RoomConfiguration(
            agents=[
                livekit_api.RoomAgentDispatch(
                    agent_name="sunrise-salon-agent"
                )
            ]
        )
    )

    return {
        "token": token.to_jwt(),
        "url": os.environ["LIVEKIT_URL"]
    }
 