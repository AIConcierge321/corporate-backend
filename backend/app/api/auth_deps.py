from fastapi import Depends, HTTPException
from typing import Set, List
import logging

from app.models.employee import Employee
from app.api.deps import get_current_user
from app.core.permissions import get_permissions_for_groups

logger = logging.getLogger(__name__)


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
            # Log detailed info server-side (MED-001: don't leak to client)
            missing = required - user_permissions
            logger.warning(
                f"Permission denied for user {current_user.id}: "
                f"missing {missing}, has {user_permissions}"
            )
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions"  # Generic message
            )
        return current_user
    return checker

