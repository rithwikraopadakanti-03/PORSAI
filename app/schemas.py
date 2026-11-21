from pydantic import BaseModel, Field
from datetime import datetime

class BookingCreate(BaseModel):
    service_id: int
    starts_at: datetime
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(min_length=5, max_length=40)

class RescheduleRequest(BaseModel):
    starts_at: datetime

class CancelRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=40)
