"""
Delegation Model - Enables "Acting On Behalf Of" for non-hierarchical relationships.

Use Cases:
- Executive Assistant → Can book for their Boss (CEO)
- Travel Coordinator → Can book for specific departments
- Temporary coverage → Employee A covers for Employee B during vacation
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from typing import Optional
from app.db.base import Base


class DelegationType(str, enum.Enum):
    """Type of delegation relationship"""
    BOOKING = "booking"          # Can book travel for target
    APPROVAL = "approval"        # Can approve on behalf of target
    VIEW = "view"                # Can view bookings for target
    FULL = "full"                # All of the above


class Delegation(Base):
    """
    Explicit delegation from one employee to another.
    
    Example: CEO delegates BOOKING rights to their Executive Assistant
    - delegator_id = CEO.id
    - delegate_id = EA.id
    - delegation_type = BOOKING
    """
    __tablename__ = "delegations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Who is granting the delegation (the boss)
    delegator_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Who receives the delegation rights (the assistant)
    delegate_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # What type of delegation
    delegation_type: Mapped[DelegationType] = mapped_column(
        SQLEnum(DelegationType, name="delegation_type"),
        default=DelegationType.BOOKING
    )
    
    # Optional: Limit to specific booking types
    # e.g., "flights" or "hotels" - NULL means all
    scope: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Time bounds (optional)
    starts_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    delegator: Mapped["Employee"] = relationship("Employee", foreign_keys=[delegator_id])
    delegate: Mapped["Employee"] = relationship("Employee", foreign_keys=[delegate_id])
