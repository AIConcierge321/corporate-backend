from fastapi import Depends, HTTPException
from typing import Set, List
from app.models.employee import Employee
from app.api.deps import get_current_user
from app.core.permissions import get_permissions_for_groups

def require_permissions(required: Set[str]):
    """
    Dependency factory to enforce granular permissions.
    """
    async def checker(current_user: Employee = Depends(get_current_user)) -> Employee:
        # Extract group names from user's groups
        user_group_names = [g.name for g in current_user.groups]
        
        user_permissions = get_permissions_for_groups(user_group_names)
        
        # Check if user has ALL required permissions (subset check)
        if not required.issubset(user_permissions):
            raise HTTPException(
                status_code=403, 
                detail=f"Missing required permissions: {required - user_permissions}"
            )
        return current_user
    return checker
