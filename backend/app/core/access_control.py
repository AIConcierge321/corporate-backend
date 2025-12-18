from sqlalchemy.orm import Session
from typing import List, Optional, Set
from app.models.employee import Employee
from app.core.permissions import Permissions, get_permissions_for_groups

class AccessControl:
    """
    Centralized logic for Hierarchy-based permissions and visibility.
    Implements the "Acting On Behalf Of" logic.
    """
    def __init__(self, db: Session, actor: Employee):
        self.db = db
        self.actor = actor
        # Calculate permissions based on groups
        # Ensure actor.groups is loaded or accessible
        group_names = [g.name for g in actor.groups] if actor.groups else []
        self.permissions = get_permissions_for_groups(group_names)

    def can(self, permission: str) -> bool:
        """
        Check if the actor has a specific hierarchical permission capability.
        """
        return permission in self.permissions

    def can_act_for(self, target_employee_id: int) -> bool:
        """
        Determines if the actor can perform actions (book, view) on behalf of the target employee.
        Rules:
        1. Self: Always allowed if they have basic self-rights.
        2. Admin: Allowed if they have BOOK_ANYONE.
        3. Manager: Allowed if target is in their hierarchy (direct or indirect).
        """
        # 1. Self interaction
        if self.actor.id == target_employee_id:
            # Assuming basic employee role always has these, but checking explicitly is safer
            return self.can(Permissions.BOOK_SELF) or self.can(Permissions.VIEW_SELF_BOOKINGS)

        # 2. Global Admin / Book Anyone
        if self.can(Permissions.BOOK_ANYONE):
            return True

        # 3. Hierarchy Check (Manager -> Subordinate)
        if self.can(Permissions.BOOK_FOR_OTHERS) or self.can(Permissions.VIEW_TEAM_BOOKINGS):
            if self._is_subordinate(target_employee_id):
                return True
        
        return False

    def get_viewable_employees(self) -> List[int]:
        """
        Return a list of employee IDs that this actor can view/manage.
        """
        if self.can(Permissions.BOOK_ANYONE) or self.can(Permissions.VIEW_ALL_BOOKINGS):
            # This implies fetching all is allowed, but returning None or specific flag 
            # might be better for the caller to handle "All" vs "List".
            # For now, let's return a list of IDs if the query isn't massive, 
            # or handle it in the service layer.
            # Returning None implies "Global Access".
            return None 

        viewable_ids = {self.actor.id}
        
        if self.can(Permissions.VIEW_TEAM_BOOKINGS) or self.can(Permissions.BOOK_FOR_OTHERS):
             subordinates = self._get_all_subordinates()
             viewable_ids.update(sub.id for sub in subordinates)
             
        return list(viewable_ids)

    def _is_subordinate(self, target_id: int) -> bool:
        """
        Check if target_id is a subordinate (direct or indirect) of actor.
        """
        # Quick check on direct reports
        for direct in self.actor.subordinates:
            if direct.id == target_id:
                return True
        
        # Deep check
        # For performance, fetching all subordinate IDs at once is better than recursive individual checks
        all_subs = self._get_all_subordinates()
        return any(s.id == target_id for s in all_subs)

    def _get_all_subordinates(self) -> List[Employee]:
        """
        Fetch all indirect subordinates.
        """
        # Simple BFS Implementation using SQLAlchemy relationship
        # Note: For very large trees, use a Recursive CTE (Common Table Expression).
        # Given the "Corporate Travel" context, teams might be manageable in memory 
        # but CTE is safer. For this file, we stay Python-side for clarity unless performance hits.
        
        subordinates = []
        queue = [s for s in self.actor.subordinates]
        visited = set([self.actor.id])
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            subordinates.append(current)
            
            # Add sub-subordinates
            queue.extend(current.subordinates)
            
        return subordinates
