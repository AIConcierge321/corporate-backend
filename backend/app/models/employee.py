import uuid
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Many-to-Many table for Employee <-> DirectoryGroup
employee_groups = Table(
    "employee_groups",
    Base.metadata,
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("directory_groups.id"), primary_key=True),
)


class DirectoryGroup(Base):
    __tablename__ = "directory_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    external_group_id: Mapped[str] = mapped_column(
        String, index=True, nullable=False
    )  # ID from IdP
    name: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="groups")
    members: Mapped[list["Employee"]] = relationship(
        secondary=employee_groups, back_populates="groups"
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    # Identity
    external_user_id: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=True
    )  # ID from IdP
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    # Profile (Synced from IdP)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String)
    job_title: Mapped[str | None] = mapped_column(String)
    department: Mapped[str | None] = mapped_column(String)
    division: Mapped[str | None] = mapped_column(String)
    cost_center: Mapped[str | None] = mapped_column(String)
    phone_number: Mapped[str | None] = mapped_column(String)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(
        String, default="active"
    )  # active, suspended, deprovisioned

    # App Settings (Local)
    travel_preferences: Mapped[dict | None] = mapped_column(JSONB)
    notification_settings: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="employees")
    groups: Mapped[list["DirectoryGroup"]] = relationship(
        secondary=employee_groups, back_populates="members"
    )

    # User as the BOOKER (bookings they created)
    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", foreign_keys="Booking.booker_id", back_populates="booker"
    )

    # Manager / Hierarchy
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee", remote_side="[Employee.id]", back_populates="subordinates"
    )
    subordinates: Mapped[list["Employee"]] = relationship("Employee", back_populates="manager")

    # User as the TRAVELER (trips they are going on)
    # travelers relationship in Booking is defined as secondary, so we can access it here if needed or just query via Booking

    # Role-based permissions
    role_assignments: Mapped[list["EmployeeRoleAssignment"]] = relationship(
        "EmployeeRoleAssignment",
        back_populates="employee",
        lazy="selectin",  # Eager load for permission checks
    )
