"""
Role Management API Endpoints

- Role Templates (CRUD)
- Role Assignments
- Permissions listing

SECURITY: Template and assignment mutations require 'manage_roles' permission.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api import deps
from app.core.access_control import AccessControl
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.employee import Employee
from app.models.role_template import (
    AVAILABLE_PERMISSIONS,
    AccessScope,
    EmployeeRoleAssignment,
    RoleTemplate,
)
from app.schemas.role import (
    AccessScopeEnum,
    AvailablePermissionsResponse,
    EmployeeRolesResponse,
    PermissionCategory,
    PermissionInfo,
    RoleAssignmentCreate,
    RoleAssignmentResponse,
    RoleTemplateCreate,
    RoleTemplateList,
    RoleTemplateResponse,
    RoleTemplateUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_manage_roles(current_user: Employee) -> None:
    """
    Check if user has permission to manage roles.
    Raises HTTPException if not authorized.
    """
    ac = AccessControl(current_user)
    if not ac.can("manage_roles"):
        logger.warning(f"User {current_user.id} attempted role management without permission")
        raise HTTPException(status_code=403, detail="You don't have permission to manage roles")


# ==================== Permissions ====================


@router.get("/permissions", response_model=AvailablePermissionsResponse)
@limiter.limit("60/minute")
async def list_available_permissions(request: Request) -> Any:
    """
    List all available permissions grouped by category.
    """
    # Group permissions by category
    categories_map = {
        "Booking": [],
        "Travel Class": [],
        "Approvals": [],
        "Visibility": [],
        "Administration": [],
    }

    for key, desc in AVAILABLE_PERMISSIONS.items():
        if key.startswith("book_"):
            cat = "Booking"
        elif key.endswith("_class"):
            cat = "Travel Class"
        elif key.startswith("approve_") or key == "override_policy":
            cat = "Approvals"
        elif key.startswith("view_"):
            cat = "Visibility"
        else:
            cat = "Administration"

        categories_map[cat].append(PermissionInfo(key=key, description=desc, category=cat))

    categories = [
        PermissionCategory(name=name, permissions=perms)
        for name, perms in categories_map.items()
        if perms
    ]

    return AvailablePermissionsResponse(
        categories=categories, all_permissions=AVAILABLE_PERMISSIONS
    )


# ==================== Role Templates ====================


@router.get("/templates", response_model=RoleTemplateList)
@limiter.limit("30/minute")
async def list_role_templates(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List all role templates for the organization.
    """
    stmt = select(RoleTemplate).where(RoleTemplate.org_id == current_user.org_id)
    result = await db.execute(stmt)
    templates = result.scalars().all()

    return RoleTemplateList(
        templates=[RoleTemplateResponse.model_validate(t) for t in templates], total=len(templates)
    )


@router.post("/templates", response_model=RoleTemplateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_role_template(
    request: Request,
    template_in: RoleTemplateCreate,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new role template.

    Requires: manage_roles permission
    """
    _require_manage_roles(current_user)

    # Validate permissions
    invalid_perms = set(template_in.permissions.keys()) - set(AVAILABLE_PERMISSIONS.keys())
    if invalid_perms:
        raise HTTPException(
            status_code=400, detail=f"Invalid permissions: {', '.join(invalid_perms)}"
        )

    template = RoleTemplate(
        org_id=current_user.org_id,
        name=template_in.name,
        description=template_in.description,
        permissions=template_in.permissions,
        default_access_scope=AccessScope(template_in.default_access_scope.value),
        is_system=False,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return RoleTemplateResponse.model_validate(template)


@router.get("/templates/{template_id}", response_model=RoleTemplateResponse)
@limiter.limit("60/minute")
async def get_role_template(
    request: Request,
    template_id: UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific role template.

    Note: Read access is allowed for all authenticated users.
    """
    stmt = select(RoleTemplate).where(
        RoleTemplate.id == template_id, RoleTemplate.org_id == current_user.org_id
    )
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise HTTPException(status_code=404, detail="Role template not found")

    return RoleTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=RoleTemplateResponse)
@limiter.limit("10/minute")
async def update_role_template(
    request: Request,
    template_id: UUID,
    template_in: RoleTemplateUpdate,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update a role template.

    Requires: manage_roles permission
    """
    _require_manage_roles(current_user)
    stmt = select(RoleTemplate).where(
        RoleTemplate.id == template_id, RoleTemplate.org_id == current_user.org_id
    )
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise HTTPException(status_code=404, detail="Role template not found")

    # Validate permissions if provided
    if template_in.permissions:
        invalid_perms = set(template_in.permissions.keys()) - set(AVAILABLE_PERMISSIONS.keys())
        if invalid_perms:
            raise HTTPException(
                status_code=400, detail=f"Invalid permissions: {', '.join(invalid_perms)}"
            )

    # Update fields
    if template_in.name is not None:
        template.name = template_in.name
    if template_in.description is not None:
        template.description = template_in.description
    if template_in.permissions is not None:
        template.permissions = template_in.permissions
    if template_in.default_access_scope is not None:
        template.default_access_scope = AccessScope(template_in.default_access_scope.value)

    await db.commit()
    await db.refresh(template)

    return RoleTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_role_template(
    request: Request,
    template_id: UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a role template (non-system only).

    Requires: manage_roles permission
    """
    _require_manage_roles(current_user)
    stmt = select(RoleTemplate).where(
        RoleTemplate.id == template_id, RoleTemplate.org_id == current_user.org_id
    )
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise HTTPException(status_code=404, detail="Role template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role templates")

    await db.delete(template)
    await db.commit()


# ==================== Role Assignments ====================


@router.post("/assign", response_model=RoleAssignmentResponse, status_code=201)
@limiter.limit("20/minute")
async def assign_role(
    request: Request,
    assignment_in: RoleAssignmentCreate,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Assign a role template to an employee with access scope.

    Requires: manage_roles permission
    """
    _require_manage_roles(current_user)
    # Verify template exists
    stmt = select(RoleTemplate).where(
        RoleTemplate.id == assignment_in.role_template_id,
        RoleTemplate.org_id == current_user.org_id,
    )
    result = await db.execute(stmt)
    template = result.scalars().first()

    if not template:
        raise HTTPException(status_code=404, detail="Role template not found")

    # Verify employee exists
    stmt = select(Employee).where(
        Employee.id == assignment_in.employee_id, Employee.org_id == current_user.org_id
    )
    result = await db.execute(stmt)
    employee = result.scalars().first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Validate scope requirements
    if (
        assignment_in.access_scope == AccessScopeEnum.INDIVIDUALS
        and not assignment_in.accessible_employee_ids
    ):
        raise HTTPException(
            status_code=400, detail="accessible_employee_ids required for 'individuals' scope"
        )

    if assignment_in.access_scope == AccessScopeEnum.GROUP and not assignment_in.accessible_groups:
        raise HTTPException(status_code=400, detail="accessible_groups required for 'group' scope")

    assignment = EmployeeRoleAssignment(
        employee_id=assignment_in.employee_id,
        role_template_id=assignment_in.role_template_id,
        access_scope=AccessScope(assignment_in.access_scope.value),
        accessible_employee_ids=assignment_in.accessible_employee_ids,
        accessible_groups=assignment_in.accessible_groups,
        is_active=True,
    )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return RoleAssignmentResponse(
        id=assignment.id,
        employee_id=assignment.employee_id,
        role_template_id=assignment.role_template_id,
        role_template_name=template.name,
        access_scope=AccessScopeEnum(assignment.access_scope.value),
        accessible_employee_ids=assignment.accessible_employee_ids,
        accessible_groups=assignment.accessible_groups,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


@router.get("/assignments/{employee_id}", response_model=EmployeeRolesResponse)
@limiter.limit("60/minute")
async def get_employee_roles(
    request: Request,
    employee_id: int,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get all role assignments for an employee with effective permissions.
    """
    # Get employee
    stmt = select(Employee).where(
        Employee.id == employee_id, Employee.org_id == current_user.org_id
    )
    result = await db.execute(stmt)
    employee = result.scalars().first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get assignments with templates (eagerly load role_template)
    stmt = (
        select(EmployeeRoleAssignment)
        .options(joinedload(EmployeeRoleAssignment.role_template))
        .where(
            EmployeeRoleAssignment.employee_id == employee_id,
            EmployeeRoleAssignment.is_active,
        )
    )
    result = await db.execute(stmt)
    assignments = result.scalars().unique().all()

    # Calculate effective permissions and accessible employees
    effective_permissions = {}
    all_accessible_ids = set()
    has_all_access = False

    for assignment in assignments:
        # Merge permissions
        template = assignment.role_template
        for perm, enabled in template.permissions.items():
            if enabled:
                effective_permissions[perm] = True

        # Calculate accessible employees
        if assignment.access_scope == AccessScope.ALL:
            has_all_access = True
        elif assignment.access_scope == AccessScope.SELF:
            all_accessible_ids.add(employee_id)
        elif assignment.access_scope == AccessScope.INDIVIDUALS:
            all_accessible_ids.add(employee_id)
            if assignment.accessible_employee_ids:
                all_accessible_ids.update(assignment.accessible_employee_ids)
        elif assignment.access_scope == AccessScope.GROUP:
            all_accessible_ids.add(employee_id)
            # Query employees in these groups
            if assignment.accessible_groups:
                group_stmt = select(Employee.id).where(
                    Employee.org_id == current_user.org_id,
                    Employee.department.in_(assignment.accessible_groups),
                )
                group_result = await db.execute(group_stmt)
                group_ids = [r[0] for r in group_result.all()]
                all_accessible_ids.update(group_ids)
        elif assignment.access_scope == AccessScope.HIERARCHY:
            # Use manager hierarchy - handled by AccessControl
            all_accessible_ids.add(employee_id)

    assignment_responses = [
        RoleAssignmentResponse(
            id=a.id,
            employee_id=a.employee_id,
            role_template_id=a.role_template_id,
            role_template_name=a.role_template.name,
            access_scope=AccessScopeEnum(a.access_scope.value),
            accessible_employee_ids=a.accessible_employee_ids,
            accessible_groups=a.accessible_groups,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in assignments
    ]

    return EmployeeRolesResponse(
        employee_id=employee_id,
        employee_name=employee.full_name,
        assignments=assignment_responses,
        effective_permissions=effective_permissions,
        accessible_employee_ids=None if has_all_access else list(all_accessible_ids),
    )


@router.delete("/assign/{assignment_id}", status_code=204)
@limiter.limit("20/minute")
async def remove_role_assignment(
    request: Request,
    assignment_id: UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Remove a role assignment.

    Requires: manage_roles permission
    """
    _require_manage_roles(current_user)

    # MED-007: Add org_id check to prevent cross-org deletion
    stmt = (
        select(EmployeeRoleAssignment)
        .join(Employee, EmployeeRoleAssignment.employee_id == Employee.id)
        .where(
            EmployeeRoleAssignment.id == assignment_id,
            Employee.org_id == current_user.org_id,  # Scope to org
        )
    )
    result = await db.execute(stmt)
    assignment = result.scalars().first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await db.delete(assignment)
    await db.commit()
