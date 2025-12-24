from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.approval import ApprovalStatus


class ApprovalRequestResponse(BaseModel):
    id: UUID
    booking_id: UUID
    approver_id: int
    status: ApprovalStatus
    reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    reason: str | None = None
