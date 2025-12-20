"""
Booking Service - Helper functions for booking operations.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.employee import Employee
from app.core.access_control import AccessControl, get_accessible_employee_ids_with_groups


async def get_bookable_employees(db: AsyncSession, current_user: Employee) -> List[Employee]:
    """
    Determine which employees the current user can book for based on role assignments.
    
    Uses the new role-based AccessControl system.
    """
    # Initialize AccessControl from user's role assignments
    ac = AccessControl(current_user)
    
    # Check if user can book at all
    can_book = ac.can("book_flights") or ac.can("book_hotels") or ac.can("book_ground")
    if not can_book:
        return []
    
    # Get accessible employee IDs (includes group-based access)
    accessible_ids = await get_accessible_employee_ids_with_groups(db, ac, current_user.org_id)
    
    if accessible_ids is None:
        # Global access (Travel Admin) - return all active employees
        result = await db.execute(
            select(Employee)
            .where(Employee.org_id == current_user.org_id, Employee.is_active == True)
        )
        return result.scalars().all()
    
    if not accessible_ids:
        return []
    
    # Fetch employee objects for accessible IDs
    result = await db.execute(
        select(Employee)
        .where(Employee.id.in_(accessible_ids), Employee.is_active == True)
    )
    return result.scalars().all()


async def check_can_book_for(db: AsyncSession, current_user: Employee, target_ids: List[int]) -> bool:
    """
    Check if current user can book for all target employees.
    
    Returns True if allowed, raises HTTPException if not.
    """
    ac = AccessControl(current_user)
    
    # Check booking permission
    can_book = ac.can("book_flights") or ac.can("book_hotels") or ac.can("book_ground")
    if not can_book:
        return False
    
    # Check each target
    for target_id in target_ids:
        if not ac.can_act_for(target_id):
            # Could be group-based - need to check DB
            accessible_ids = await get_accessible_employee_ids_with_groups(db, ac, current_user.org_id)
            if accessible_ids is not None and target_id not in accessible_ids:
                return False
    
    return True
