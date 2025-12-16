from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Boolean, Table, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import List, Optional
from app.db.base import Base

# Booking Travelers Association (Many-to-Many)
booking_travelers = Table(
    "booking_travelers",
    Base.metadata,
    Column("booking_id", UUID(as_uuid=True), ForeignKey("bookings.id"), primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
)

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Who created the booking
    booker_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    
    status: Mapped[str] = mapped_column(String, default="draft") # draft, confirmed, cancelled, completed
    total_amount: Mapped[Optional[float]] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String, default="USD")
    
    # Metadata
    trip_name: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    booker: Mapped["Employee"] = relationship("Employee", foreign_keys=[booker_id], back_populates="bookings")
    travelers: Mapped[List["Employee"]] = relationship("Employee", secondary=booking_travelers)
