"""
Role API Schemas
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class AccessScopeEnum(str, Enum):
    """Access scope for role assignments."""

    SELF = "self"
    INDIVIDUALS = "individuals"
    GROUP = "group"
    HIERARCHY = "hierarchy"
    ALL = "all"


# ==================== Permission Info ====================


class PermissionInfo(BaseModel):
    """Information about a single permission."""

    key: str
    description: str
    category: str


# ==================== Role Templates ====================


class RoleTemplateBase(BaseModel):
    """Base schema for role templates."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    permissions: dict[str, bool] = Field(default_factory=dict)
    default_access_scope: AccessScopeEnum = AccessScopeEnum.SELF


class RoleTemplateCreate(RoleTemplateBase):
    """Schema for creating a role template."""

    pass


class RoleTemplateUpdate(BaseModel):
    """Schema for updating a role template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: dict[str, bool] | None = None
    default_access_scope: AccessScopeEnum | None = None


class RoleTemplateResponse(RoleTemplateBase):
    """Response schema for a role template."""

    id: UUID
    org_id: UUID
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleTemplateList(BaseModel):
    """List of role templates."""

    templates: list[RoleTemplateResponse]
    total: int


# ==================== Role Assignments ====================


class RoleAssignmentCreate(BaseModel):
    """Schema for assigning a role to an employee."""

    employee_id: int
    role_template_id: UUID
    access_scope: AccessScopeEnum

    # For 'individuals' scope
    accessible_employee_ids: list[int] | None = None

    # For 'group' scope
    accessible_groups: list[str] | None = None


class RoleAssignmentUpdate(BaseModel):
    """Schema for updating a role assignment."""

    access_scope: AccessScopeEnum | None = None
    accessible_employee_ids: list[int] | None = None
    accessible_groups: list[str] | None = None
    is_active: bool | None = None


class RoleAssignmentResponse(BaseModel):
    """Response schema for a role assignment."""

    id: UUID
    employee_id: int
    role_template_id: UUID
    role_template_name: str
    access_scope: AccessScopeEnum
    accessible_employee_ids: list[int] | None = None
    accessible_groups: list[str] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmployeeRolesResponse(BaseModel):
    """Response with all roles for an employee."""

    employee_id: int
    employee_name: str
    assignments: list[RoleAssignmentResponse]
    effective_permissions: dict[str, bool]
    accessible_employee_ids: list[int] | None  # None = all access


# ==================== Permission Categories ====================


class PermissionCategory(BaseModel):
    """Category of permissions."""

    name: str
    permissions: list[PermissionInfo]


class AvailablePermissionsResponse(BaseModel):
    """All available permissions grouped by category."""

    categories: list[PermissionCategory]
    all_permissions: dict[str, str]
