from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class BookingBase(BaseModel):
    trip_name: Optional[str] = None

class BookingCreate(BookingBase):
    traveler_ids: List[int] # Who are we booking for?

from app.models.booking import BookingStatus, PolicyStatus

class BookingResponse(BookingBase):
    id: UUID
    status: BookingStatus
    policy_status: Optional[PolicyStatus] = None
    approval_required: bool = False
    
    booker_id: int
    traveler_ids: List[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookableEmployee(BaseModel):
    id: int
    full_name: str
    email: str
