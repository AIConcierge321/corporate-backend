"""
Role API Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID
from enum import Enum


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
    description: Optional[str] = None
    permissions: Dict[str, bool] = Field(default_factory=dict)
    default_access_scope: AccessScopeEnum = AccessScopeEnum.SELF


class RoleTemplateCreate(RoleTemplateBase):
    """Schema for creating a role template."""
    pass


class RoleTemplateUpdate(BaseModel):
    """Schema for updating a role template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None
    default_access_scope: Optional[AccessScopeEnum] = None


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
    templates: List[RoleTemplateResponse]
    total: int


# ==================== Role Assignments ====================

class RoleAssignmentCreate(BaseModel):
    """Schema for assigning a role to an employee."""
    employee_id: int
    role_template_id: UUID
    access_scope: AccessScopeEnum
    
    # For 'individuals' scope
    accessible_employee_ids: Optional[List[int]] = None
    
    # For 'group' scope
    accessible_groups: Optional[List[str]] = None


class RoleAssignmentUpdate(BaseModel):
    """Schema for updating a role assignment."""
    access_scope: Optional[AccessScopeEnum] = None
    accessible_employee_ids: Optional[List[int]] = None
    accessible_groups: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RoleAssignmentResponse(BaseModel):
    """Response schema for a role assignment."""
    id: UUID
    employee_id: int
    role_template_id: UUID
    role_template_name: str
    access_scope: AccessScopeEnum
    accessible_employee_ids: Optional[List[int]] = None
    accessible_groups: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmployeeRolesResponse(BaseModel):
    """Response with all roles for an employee."""
    employee_id: int
    employee_name: str
    assignments: List[RoleAssignmentResponse]
    effective_permissions: Dict[str, bool]
    accessible_employee_ids: Optional[List[int]]  # None = all access


# ==================== Permission Categories ====================

class PermissionCategory(BaseModel):
    """Category of permissions."""
    name: str
    permissions: List[PermissionInfo]


class AvailablePermissionsResponse(BaseModel):
    """All available permissions grouped by category."""
    categories: List[PermissionCategory]
    all_permissions: Dict[str, str]
