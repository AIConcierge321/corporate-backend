from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from typing import Optional
from app.db.base import Base

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    
    # Who currently needs to approve (The "Approver")
    approver_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", values_callable=lambda obj: [e.value for e in obj]), 
        default=ApprovalStatus.PENDING
    )
    
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Reason for rejection or note
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", backref="approval_requests")
    approver: Mapped["Employee"] = relationship("Employee", foreign_keys=[approver_id])
