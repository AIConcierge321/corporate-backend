from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BookingBase(BaseModel):
    trip_name: str | None = None


class BookingCreate(BookingBase):
    traveler_ids: list[int]  # Who are we booking for?
    total_amount: float = 0
    travel_class: str = "economy"
    start_date: datetime | None = None


from app.models.booking import BookingStatus, PolicyStatus


class BookingResponse(BookingBase):
    id: UUID
    status: BookingStatus
    policy_status: PolicyStatus | None = None
    approval_required: bool = False

    booker_id: int
    traveler_ids: list[int]
    created_at: datetime

    class Config:
        from_attributes = True


class BookableEmployee(BaseModel):
    id: int
    full_name: str
    email: str
