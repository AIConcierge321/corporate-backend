"""
AccessControl - Centralized logic for Hierarchy + Delegation based permissions.

Implements:
- Hierarchy-based visibility (Manager → Subordinates)
- Delegation-based visibility (EA → Boss via explicit grant)
- "Acting On Behalf Of" logic
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Set, Union
from datetime import datetime, timezone

from app.models.employee import Employee
from app.models.delegation import Delegation, DelegationType
from app.core.permissions import Permissions, get_permissions_for_groups


class AccessControl:
    """
    Centralized logic for Hierarchy + Delegation based permissions.
    """
    def __init__(self, db: Session, actor: Employee):
        self.db = db
        self.actor = actor
        # Calculate permissions based on groups
        group_names = [g.name for g in actor.groups] if actor.groups else []
        self.permissions = get_permissions_for_groups(group_names)
        
        # Cache for delegations (lazy loaded)
        self._delegations_cache: Optional[List[int]] = None

    def can(self, permission: str) -> bool:
        """
        Check if the actor has a specific permission capability.
        """
        return permission in self.permissions

    def can_act_for(self, target_employee_id: int, action_type: str = "booking") -> bool:
        """
        Determines if the actor can perform actions on behalf of the target employee.
        
        Rules (in order of precedence):
        1. Self: Always allowed if they have basic self-rights.
        2. Admin: Allowed if they have BOOK_ANYONE.
        3. Delegation: Allowed if explicit delegation exists.
        4. Hierarchy: Allowed if target is in their subordinate tree.
        """
        # 1. Self interaction
        if self.actor.id == target_employee_id:
            return self.can(Permissions.BOOK_SELF) or self.can(Permissions.VIEW_SELF_BOOKINGS)

        # 2. Global Admin / Book Anyone
        if self.can(Permissions.BOOK_ANYONE):
            return True

        # 3. Delegation Check (EA → Boss)
        delegated_ids = self._get_delegated_employee_ids(action_type)
        if target_employee_id in delegated_ids:
            return True

        # 4. Hierarchy Check (Manager → Subordinate)
        if self.can(Permissions.BOOK_FOR_OTHERS) or self.can(Permissions.VIEW_TEAM_BOOKINGS):
            if self._is_subordinate(target_employee_id):
                return True
        
        return False

    def get_viewable_employees(self) -> Optional[List[int]]:
        """
        Return a list of employee IDs that this actor can view/manage.
        Returns None for global access (admin).
        """
        if self.can(Permissions.BOOK_ANYONE) or self.can(Permissions.VIEW_ALL_BOOKINGS):
            return None  # Global Access

        viewable_ids = {self.actor.id}
        
        # Add delegated employees
        delegated_ids = self._get_delegated_employee_ids("view")
        viewable_ids.update(delegated_ids)
        
        # Add subordinates
        if self.can(Permissions.VIEW_TEAM_BOOKINGS) or self.can(Permissions.BOOK_FOR_OTHERS):
            subordinates = self._get_all_subordinates()
            viewable_ids.update(sub.id for sub in subordinates)
             
        return list(viewable_ids)

    def get_bookable_employee_ids(self) -> Optional[List[int]]:
        """
        Return a list of employee IDs that this actor can book for.
        Returns None for global access (admin).
        """
        if self.can(Permissions.BOOK_ANYONE):
            return None  # Global Access

        bookable_ids = {self.actor.id}
        
        # Add delegated employees (booking type)
        delegated_ids = self._get_delegated_employee_ids("booking")
        bookable_ids.update(delegated_ids)
        
        # Add subordinates if manager
        if self.can(Permissions.BOOK_FOR_OTHERS):
            subordinates = self._get_all_subordinates()
            bookable_ids.update(sub.id for sub in subordinates if sub.is_active)
             
        return list(bookable_ids)

    def _get_delegated_employee_ids(self, action_type: str = "booking") -> Set[int]:
        """
        Get employee IDs that have delegated rights to this actor.
        
        action_type: "booking", "approval", "view", or "full"
        """
        # Map action type to delegation types that satisfy it
        type_map = {
            "booking": [DelegationType.BOOKING, DelegationType.FULL],
            "approval": [DelegationType.APPROVAL, DelegationType.FULL],
            "view": [DelegationType.VIEW, DelegationType.BOOKING, DelegationType.APPROVAL, DelegationType.FULL],
        }
        
        allowed_types = type_map.get(action_type, [DelegationType.FULL])
        now = datetime.now(timezone.utc)
        
        delegated_ids = set()
        
        # Note: This is synchronous. For async context, caller should pre-fetch delegations.
        # For now, we assume delegations are eagerly loaded or we're in sync context.
        # In production, consider caching or eager loading.
        
        # Query delegations where this actor is the delegate
        # This requires sync session - for async, refactor to pass pre-fetched delegations
        try:
            # Try to use the session if it supports execute
            from sqlalchemy import select as sync_select
            stmt = sync_select(Delegation).where(
                Delegation.delegate_id == self.actor.id,
                Delegation.is_active == True,
                Delegation.delegation_type.in_(allowed_types)
            )
            
            # Filter by time bounds
            result = self.db.execute(stmt)
            for d in result.scalars().all():
                # Check time bounds
                if d.starts_at and d.starts_at > now:
                    continue
                if d.expires_at and d.expires_at < now:
                    continue
                delegated_ids.add(d.delegator_id)
        except Exception:
            # If session doesn't support sync execute, return empty
            # This is a fallback - proper implementation should handle async
            pass
            
        return delegated_ids

    def _is_subordinate(self, target_id: int) -> bool:
        """
        Check if target_id is a subordinate (direct or indirect) of actor.
        """
        # Quick check on direct reports
        if hasattr(self.actor, 'subordinates') and self.actor.subordinates:
            for direct in self.actor.subordinates:
                if direct.id == target_id:
                    return True
        
        # Deep check
        all_subs = self._get_all_subordinates()
        return any(s.id == target_id for s in all_subs)

    def _get_all_subordinates(self) -> List[Employee]:
        """
        Fetch all subordinates (direct and indirect) using BFS.
        """
        subordinates = []
        
        if not hasattr(self.actor, 'subordinates') or not self.actor.subordinates:
            return subordinates
            
        queue = [s for s in self.actor.subordinates]
        visited = {self.actor.id}
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            subordinates.append(current)
            
            # Add sub-subordinates
            if hasattr(current, 'subordinates') and current.subordinates:
                queue.extend(current.subordinates)
            
        return subordinates
