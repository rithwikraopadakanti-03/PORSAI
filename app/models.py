from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Stylist(Base):
    __tablename__ = "stylists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    services_text: Mapped[str] = mapped_column(Text)
    weekdays: Mapped[str] = mapped_column(String(30))  # Mon,Tue,...
    start_hour: Mapped[int] = mapped_column(Integer)
    end_hour: Mapped[int] = mapped_column(Integer)

class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    stylist_id: Mapped[int] = mapped_column(ForeignKey("stylists.id"))
    price_text: Mapped[str] = mapped_column(String(100))
    stylist: Mapped[Stylist] = relationship()

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("stylist_id", "starts_at", name="uq_stylist_slot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stylist_id: Mapped[int] = mapped_column(ForeignKey("stylists.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    starts_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="booked")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
