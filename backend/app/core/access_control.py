"""
AccessControl - Centralized logic for Role-based permissions and access scopes.

Updated to use dynamic RoleTemplates from database.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.role_template import AccessScope, EmployeeRoleAssignment


class AccessControl:
    """
    Role-based access control using dynamic role templates.

    Permissions come from RoleTemplate.permissions (JSONB).
    Access scope comes from EmployeeRoleAssignment.access_scope.

    Note: This class works synchronously with pre-loaded role_assignments.
    For async operations (like group/hierarchy lookups), use helper functions.
    """

    def __init__(self, actor: Employee):
        """
        Initialize AccessControl for an actor.

        Note: actor.role_assignments should be eagerly loaded (lazy="selectin").
        """
        self.actor = actor
        self._effective_permissions: dict = {}
        self._accessible_ids: set[int] = {actor.id}  # Always includes self
        self._has_global_access: bool = False
        self._accessible_groups: set[str] = set()
        self._uses_hierarchy: bool = False

        # Pre-compute permissions and access from loaded assignments
        self._compute_effective_permissions()

    def _compute_effective_permissions(self):
        """Compute effective permissions from all role assignments."""
        assignments = getattr(self.actor, "role_assignments", None) or []

        for assignment in assignments:
            if not assignment.is_active:
                continue

            template = getattr(assignment, "role_template", None)
            if not template:
                continue

            # Merge permissions (any True wins)
            for perm, enabled in (template.permissions or {}).items():
                if enabled:
                    self._effective_permissions[perm] = True

            # Process access scope
            self._process_access_scope(assignment)

    def _process_access_scope(self, assignment: EmployeeRoleAssignment):
        """Process access scope from assignment."""
        scope = assignment.access_scope

        if scope == AccessScope.ALL:
            self._has_global_access = True

        elif scope == AccessScope.SELF:
            # Already included
            pass

        elif scope == AccessScope.INDIVIDUALS:
            if assignment.accessible_employee_ids:
                self._accessible_ids.update(assignment.accessible_employee_ids)

        elif scope == AccessScope.GROUP:
            if assignment.accessible_groups:
                self._accessible_groups.update(assignment.accessible_groups)

        elif scope == AccessScope.HIERARCHY:
            # Mark that hierarchy lookup is needed
            self._uses_hierarchy = True

    def can(self, permission: str) -> bool:
        """Check if the actor has a specific permission."""
        return self._effective_permissions.get(permission, False)

    def can_act_for(self, target_employee_id: int) -> bool:
        """
        Check if actor can perform actions for target employee.

        Note: For complete check including groups/hierarchy, use
        get_accessible_employee_ids_with_groups() async function.
        """
        # Self always allowed if they have any booking permission
        if self.actor.id == target_employee_id:
            return True

        # Global access
        if self._has_global_access:
            return True

        # Check if target is in directly accessible IDs (individuals)
        return target_employee_id in self._accessible_ids

    def get_direct_accessible_ids(self) -> set[int] | None:
        """
        Get directly accessible employee IDs (self + individuals).
        Returns None for global access.

        Note: Does NOT include group/hierarchy - use async function for complete list.
        """
        if self._has_global_access:
            return None
        return self._accessible_ids

    def get_travel_class_eligibility(self) -> list[str]:
        """Get list of travel classes this actor is eligible for."""
        classes = []
        if self.can("economy_class"):
            classes.append("economy")
        if self.can("premium_economy_class"):
            classes.append("premium_economy")
        if self.can("business_class"):
            classes.append("business")
        if self.can("first_class"):
            classes.append("first")
        return classes

    def is_eligible_for_class(self, travel_class: str) -> bool:
        """Check if actor is eligible for a specific travel class."""
        class_map = {
            "economy": "economy_class",
            "premium_economy": "premium_economy_class",
            "business": "business_class",
            "first": "first_class",
        }
        perm = class_map.get(travel_class.lower())
        return self.can(perm) if perm else False


async def get_accessible_employee_ids_with_groups(
    db: AsyncSession, access_control: AccessControl, org_id
) -> list[int] | None:
    """
    Get accessible employee IDs including group and hierarchy access.

    This is the async version that queries the database.
    Returns None for global access.
    """
    if access_control._has_global_access:
        return None

    accessible_ids = set(access_control._accessible_ids)

    # Add employees from accessible groups (departments)
    if access_control._accessible_groups:
        stmt = select(Employee.id).where(
            Employee.org_id == org_id,
            Employee.is_active,
            Employee.department.in_(access_control._accessible_groups),
        )
        result = await db.execute(stmt)
        group_ids = [r[0] for r in result.all()]
        accessible_ids.update(group_ids)

    # Add subordinates if hierarchy scope is used
    if access_control._uses_hierarchy:
        subordinate_ids = await _get_all_subordinate_ids(db, access_control.actor.id)
        accessible_ids.update(subordinate_ids)

    return list(accessible_ids) if accessible_ids else []


async def _get_all_subordinate_ids(db: AsyncSession, manager_id: int) -> list[int]:
    """
    Get all subordinate IDs using recursive hierarchy traversal.
    """
    subordinate_ids = []

    # BFS to find all subordinates
    queue = [manager_id]
    visited = {manager_id}

    while queue:
        current_id = queue.pop(0)

        # Find direct reports
        stmt = select(Employee.id).where(Employee.manager_id == current_id, Employee.is_active)
        result = await db.execute(stmt)
        direct_reports = [r[0] for r in result.all()]

        for sub_id in direct_reports:
            if sub_id not in visited:
                visited.add(sub_id)
                subordinate_ids.append(sub_id)
                queue.append(sub_id)

    return subordinate_ids
