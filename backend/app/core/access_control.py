"""
AccessControl - Centralized logic for Role-based permissions and access scopes.

Updated to use dynamic RoleTemplates from database instead of hardcoded groups.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Set
from datetime import datetime, timezone

from app.models.employee import Employee
from app.models.role_template import RoleTemplate, EmployeeRoleAssignment, AccessScope


class AccessControl:
    """
    Role-based access control using dynamic role templates.
    
    Permissions come from RoleTemplate.permissions (JSONB).
    Access scope comes from EmployeeRoleAssignment.access_scope.
    """
    
    def __init__(self, actor: Employee):
        """
        Initialize AccessControl for an actor.
        
        Note: actor.role_assignments should be eagerly loaded (lazy="selectin").
        """
        self.actor = actor
        self._effective_permissions: Optional[dict] = None
        self._accessible_ids: Optional[Set[int]] = None
        self._has_global_access: bool = False
        
        # Pre-compute permissions and access
        self._compute_effective_permissions()
    
    def _compute_effective_permissions(self):
        """Compute effective permissions from all role assignments."""
        self._effective_permissions = {}
        self._accessible_ids = {self.actor.id}  # Always includes self
        
        assignments = getattr(self.actor, 'role_assignments', []) or []
        
        for assignment in assignments:
            if not assignment.is_active:
                continue
            
            template = assignment.role_template
            if not template:
                continue
            
            # Merge permissions (any True wins)
            for perm, enabled in (template.permissions or {}).items():
                if enabled:
                    self._effective_permissions[perm] = True
            
            # Compute accessible employee IDs based on scope
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
            # Groups are handled separately by querying employees in those departments
            # Store the groups for later lookup
            if not hasattr(self, '_accessible_groups'):
                self._accessible_groups = set()
            if assignment.accessible_groups:
                self._accessible_groups.update(assignment.accessible_groups)
        
        elif scope == AccessScope.HIERARCHY:
            # Hierarchy-based access uses manager/subordinate relationship
            # Get all subordinates
            subordinates = self._get_all_subordinates()
            self._accessible_ids.update(s.id for s in subordinates)
    
    def can(self, permission: str) -> bool:
        """
        Check if the actor has a specific permission.
        """
        if self._effective_permissions is None:
            self._compute_effective_permissions()
        return self._effective_permissions.get(permission, False)
    
    def can_act_for(self, target_employee_id: int) -> bool:
        """
        Check if actor can perform actions for target employee.
        """
        # Self always allowed if they have any booking permission
        if self.actor.id == target_employee_id:
            return any(self.can(p) for p in ['book_flights', 'book_hotels', 'book_ground'])
        
        # Global access
        if self._has_global_access:
            return True
        
        # Check if target is in accessible IDs
        if target_employee_id in self._accessible_ids:
            return True
        
        return False
    
    def get_accessible_employee_ids(self) -> Optional[List[int]]:
        """
        Get list of employee IDs this actor can access.
        Returns None for global access.
        """
        if self._has_global_access:
            return None
        
        return list(self._accessible_ids)
    
    def get_travel_class_eligibility(self) -> List[str]:
        """
        Get list of travel classes this actor is eligible for.
        """
        classes = []
        if self.can('economy_class'):
            classes.append('economy')
        if self.can('premium_economy_class'):
            classes.append('premium_economy')
        if self.can('business_class'):
            classes.append('business')
        if self.can('first_class'):
            classes.append('first')
        return classes
    
    def is_eligible_for_class(self, travel_class: str) -> bool:
        """
        Check if actor is eligible for a specific travel class.
        """
        class_map = {
            'economy': 'economy_class',
            'premium_economy': 'premium_economy_class',
            'business': 'business_class',
            'first': 'first_class',
        }
        perm = class_map.get(travel_class.lower())
        return self.can(perm) if perm else False
    
    def _get_all_subordinates(self) -> List[Employee]:
        """
        Get all subordinates using hierarchy (BFS traversal).
        """
        subordinates = []
        
        if not hasattr(self.actor, 'subordinates') or not self.actor.subordinates:
            return subordinates
        
        queue = list(self.actor.subordinates)
        visited = {self.actor.id}
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            subordinates.append(current)
            
            if hasattr(current, 'subordinates') and current.subordinates:
                queue.extend(current.subordinates)
        
        return subordinates


async def get_accessible_employee_ids_with_groups(
    db: AsyncSession,
    access_control: AccessControl,
    org_id
) -> Optional[List[int]]:
    """
    Get accessible employee IDs including group-based access.
    
    This queries the database for employees in accessible groups.
    """
    if access_control._has_global_access:
        return None
    
    accessible_ids = set(access_control._accessible_ids)
    
    # Add employees from accessible groups
    if hasattr(access_control, '_accessible_groups') and access_control._accessible_groups:
        stmt = select(Employee.id).where(
            Employee.org_id == org_id,
            Employee.department.in_(access_control._accessible_groups)
        )
        result = await db.execute(stmt)
        group_ids = [r[0] for r in result.all()]
        accessible_ids.update(group_ids)
    
    return list(accessible_ids)
