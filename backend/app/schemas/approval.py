from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.approval import ApprovalStatus

class ApprovalRequestResponse(BaseModel):
    id: UUID
    booking_id: UUID
    approver_id: int
    status: ApprovalStatus
    reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApprovalAction(BaseModel):
    reason: Optional[str] = None
