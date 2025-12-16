from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Boolean, Table, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.db.base import Base
from typing import List, Optional

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
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    external_group_id: Mapped[str] = mapped_column(String, index=True, nullable=False) # ID from IdP
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="groups")
    members: Mapped[List["Employee"]] = relationship(secondary=employee_groups, back_populates="groups")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Identity
    external_user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True) # ID from IdP
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # Profile (Synced from IdP)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String, default="active") # active, suspended, deprovisioned
    
    # App Settings (Local)
    travel_preferences: Mapped[Optional[dict]] = mapped_column(JSONB)
    notification_settings: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="employees")
    groups: Mapped[List["DirectoryGroup"]] = relationship(secondary=employee_groups, back_populates="members")
    
    # User as the BOOKER (bookings they created)
    bookings: Mapped[List["Booking"]] = relationship("Booking", foreign_keys="Booking.booker_id", back_populates="booker")
    
    # User as the TRAVELER (trips they are going on)
    # travelers relationship in Booking is defined as secondary, so we can access it here if needed or just query via Booking

