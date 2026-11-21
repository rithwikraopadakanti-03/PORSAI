import os
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from livekit import api as livekit_api
from .database import Base, engine, get_db
from .models import Stylist, Service, Booking
from .schemas import BookingCreate, RescheduleRequest, CancelRequest
from .seed import seed

TZ = ZoneInfo("Asia/Kolkata")
app = FastAPI(title="Sunrise Salon Voice Agent API")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    from .database import SessionLocal
    db = SessionLocal()
    try: seed(db)
    finally: db.close()

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.get("/api/business")
def business():
    return {
      "name": "Sunrise Salon", "address": "12 Lake Road, Indiranagar, Bengaluru",
      "timezone": "Asia/Kolkata", "slot_minutes": 30, "closed": ["Sunday"],
      "cancellation_policy": "Free cancellation up to 2 hours before the appointment.",
      "faqs": {"payment": "Cash, UPI and cards.", "walk_ins": "Walk-ins are welcome; booked customers are served first.",
               "parking": "Street parking only.", "late_arrival": "More than 15 minutes late, the booking may be moved to the next free slot.",
               "discounts": "No discounts right now.", "membership": "No membership or package information on file."},
      "not_offered": ["nail art", "waxing", "makeup", "tattoos", "home service"]
    }

@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "price": s.price_text, "stylist": s.stylist.name}
            for s in db.query(Service).all()]

def slots_for(service: Service, day: date, db: Session):
    stylist = service.stylist
    weekday = day.strftime("%a")
    if weekday not in stylist.weekdays.split(","): return []
    result, current = [], datetime.combine(day, time(stylist.start_hour), TZ)
    end = datetime.combine(day, time(stylist.end_hour), TZ)
    while current + timedelta(minutes=30) <= end:
        occupied = db.query(Booking).filter(Booking.stylist_id == stylist.id,
                    Booking.starts_at == current, Booking.status == "booked").first()
        if not occupied: result.append(current.isoformat())
        current += timedelta(minutes=30)
    return result

@app.get("/api/availability")
def availability(service_id: int, date: date, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service: raise HTTPException(404, "Service not found")
    return {"service": service.name, "stylist": service.stylist.name, "date": date.isoformat(),
            "available_slots": slots_for(service, date, db)}

@app.post("/api/bookings")
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service: raise HTTPException(404, "Service not found")
    start = payload.starts_at.astimezone(TZ)
    if start.minute not in (0, 30) or start.second or start.microsecond:
        raise HTTPException(400, "Appointments must start on a 30-minute boundary.")
    if start not in [datetime.fromisoformat(x) for x in slots_for(service, start.date(), db)]:
        raise HTTPException(409, "That slot is not available. Please choose another.")
    booking = Booking(stylist_id=service.stylist_id, service_id=service.id, starts_at=start,
                      customer_name=payload.customer_name, customer_phone=payload.customer_phone,
                      status="booked", created_at=datetime.now(TZ))
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That slot was just booked by someone else. Please choose another.")
    db.refresh(booking)
    return {"booking_id": booking.id, "service": service.name, "stylist": service.stylist.name,
            "starts_at": booking.starts_at.isoformat(), "status": booking.status}

@app.patch("/api/bookings/{booking_id}/reschedule")
def reschedule(booking_id: int, payload: RescheduleRequest, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.status != "booked": raise HTTPException(404, "Booking not found")
    start = payload.starts_at.astimezone(TZ)
    service = db.get(Service, booking.service_id)
    if start not in [datetime.fromisoformat(x) for x in slots_for(service, start.date(), db)]:
        raise HTTPException(409, "That slot is not available.")
    booking.starts_at = start
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That slot was just booked. Please choose another.")
    return {"booking_id": booking.id, "starts_at": start.isoformat(), "status": "rescheduled"}

@app.post("/api/bookings/{booking_id}/cancel")
def cancel(booking_id: int, payload: CancelRequest, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.status != "booked" or booking.customer_phone != payload.phone:
        raise HTTPException(404, "Booking not found")
    now = datetime.now(TZ)
    starts = booking.starts_at.astimezone(TZ)
    free = now <= starts - timedelta(hours=2)
    booking.status = "cancelled"
    db.commit()
    return {"booking_id": booking.id, "status": "cancelled",
            "free_cancellation": free,
            "message": "Cancelled free of charge." if free else "Cancelled; this is less than 2 hours before the appointment, so it is not free."}

@app.post("/api/livekit/token")
def livekit_token():
    if not all(os.getenv(k) for k in ("LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")):
        raise HTTPException(503, "LiveKit credentials are not configured.")
    token = livekit_api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
    token.with_identity("web-caller").with_name("Sunrise Salon caller").with_grants(
        livekit_api.VideoGrants(room_join=True, room=os.getenv("LIVEKIT_ROOM", "sunrise-salon")))
    return {"token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}
