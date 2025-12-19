"""
Role Template Models

- RoleTemplate: Customizable role with permissions (stored as JSONB)
- EmployeeRoleAssignment: Links employees to roles with access scope
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
import enum
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.organization import Organization


class AccessScope(str, enum.Enum):
    """Defines who an employee can act for."""
    SELF = "self"                 # Only themselves
    INDIVIDUALS = "individuals"   # Specific named people (EA → CEO)
    GROUP = "group"               # Department/team members
    HIERARCHY = "hierarchy"       # Their subordinates (via manager_id)
    ALL = "all"                   # Everyone in org


# All available permissions
AVAILABLE_PERMISSIONS = {
    # Booking Actions
    "book_flights": "Can book flights",
    "book_hotels": "Can book hotels",
    "book_ground": "Can book ground transport",
    "book_other": "Can book other travel services",
    
    # Travel Class Eligibility
    "economy_class": "Eligible for economy class",
    "premium_economy_class": "Eligible for premium economy class",
    "business_class": "Eligible for business class",
    "first_class": "Eligible for first class",
    
    # Approvals
    "approve_travel": "Can approve travel requests",
    "approve_expenses": "Can approve expense reports",
    "override_policy": "Can override policy violations",
    
    # Visibility
    "view_own_bookings": "Can view own bookings",
    "view_team_bookings": "Can view team bookings",
    "view_all_bookings": "Can view all org bookings",
    
    # Administration
    "view_analytics": "Can view analytics dashboard",
    "manage_policies": "Can edit travel policies",
    "manage_users": "Can manage employees",
    "manage_roles": "Can create/edit role templates",
    "manage_destinations": "Can manage destinations",
}


class RoleTemplate(Base):
    """
    Customizable role template with permissions.
    
    Example: "Executive Assistant" role with book_flights, book_hotels
    but NOT business_class.
    """
    __tablename__ = "role_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # System roles (Employee, Manager, Admin) cannot be deleted
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Permissions stored as JSONB: {"book_flights": true, "business_class": false}
    permissions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Default access scope for this role (can be overridden per assignment)
    default_access_scope: Mapped[AccessScope] = mapped_column(
        SQLEnum(AccessScope, name="access_scope"),
        default=AccessScope.SELF
    )
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="role_templates")
    assignments: Mapped[List["EmployeeRoleAssignment"]] = relationship("EmployeeRoleAssignment", back_populates="role_template")


class EmployeeRoleAssignment(Base):
    """
    Assigns a role template to an employee with a specific access scope.
    
    Example: Employee #42 (EA) gets "Executive Assistant" role with
    access_scope="individuals" and accessible_employee_ids=[1] (CEO).
    """
    __tablename__ = "employee_role_assignments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    role_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("role_templates.id"), nullable=False)
    
    # Access Scope - WHO can this employee act for?
    access_scope: Mapped[AccessScope] = mapped_column(
        SQLEnum(AccessScope, name="access_scope", create_type=False),
        nullable=False
    )
    
    # For 'individuals' scope: list of specific employee IDs
    accessible_employee_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    
    # For 'group' scope: list of department/group names
    accessible_groups: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Is this assignment active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="role_assignments")
    role_template: Mapped["RoleTemplate"] = relationship("RoleTemplate", back_populates="assignments")
