from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.employee import Employee
from app.core.permissions import Permissions, get_permissions_for_groups

async def get_bookable_employees(db: AsyncSession, current_user: Employee) -> List[Employee]:
    """
    Determine which employees the current user can book for based on permissions.
    """
    from app.core.access_control import AccessControl
    ac = AccessControl(db, current_user)
    
    # Check simple permission first for efficiency
    if ac.can(Permissions.BOOK_ANYONE):
        # Admin: Return all active employees in Org
        result = await db.execute(select(Employee).where(Employee.org_id == current_user.org_id, Employee.is_active == True))
        return result.scalars().all()
        
    bookable_ids = {current_user.id}
    
    # Manager Logic
    if ac.can(Permissions.BOOK_FOR_OTHERS):
        # In AccessControl, we use _get_all_subordinates to find the tree
        subordinates = ac._get_all_subordinates()
        for s in subordinates:
             if s.is_active:
                bookable_ids.add(s.id)
    
    # Fetch objects
    stmt = select(Employee).where(Employee.id.in_(list(bookable_ids)))
    result = await db.execute(stmt)
    return result.scalars().all()
