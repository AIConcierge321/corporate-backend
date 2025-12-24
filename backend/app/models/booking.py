import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BookingStatus(str, enum.Enum):
    DRAFT = "draft"
    POLICY_EVALUATED = "policy_evaluated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REQUIRES_ATTENTION = "requires_attention"
    REJECTED = "rejected"


class PolicyStatus(str, enum.Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class TravelerRole(str, enum.Enum):
    PRIMARY = "primary"
    ADDITIONAL = "additional"


class BookingTraveler(Base):
    __tablename__ = "booking_travelers"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), primary_key=True)

    role: Mapped[TravelerRole] = mapped_column(
        Enum(TravelerRole, name="traveler_role"), default=TravelerRole.PRIMARY
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee")
    booking: Mapped["Booking"] = relationship("Booking", back_populates="travelers_association")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    # Who created the booking (The "Booker")
    booker_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)

    # State & Lifecycle
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus, name="booking_status", values_callable=lambda obj: [e.value for e in obj]
        ),
        default=BookingStatus.DRAFT,
    )
    policy_status: Mapped[PolicyStatus | None] = mapped_column(
        Enum(
            PolicyStatus, name="policy_status", values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=True,
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)

    total_amount: Mapped[float | None] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String, default="USD")
    trip_name: Mapped[str | None] = mapped_column(String)

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    travel_class: Mapped[str | None] = mapped_column(
        String, default="economy"
    )  # economy, business, first

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    booker: Mapped["Employee"] = relationship(
        "Employee", foreign_keys=[booker_id], back_populates="bookings"
    )

    # Rich Association to Travelers
    travelers_association: Mapped[list["BookingTraveler"]] = relationship(
        "BookingTraveler", back_populates="booking", cascade="all, delete-orphan"
    )

    # Shortcut to get traveler objects directly (read-only mostly)
    travelers: Mapped[list["Employee"]] = relationship(
        "Employee", secondary="booking_travelers", viewonly=True
    )

    @property
    def traveler_ids(self) -> list[int]:
        return [t.id for t in self.travelers]
