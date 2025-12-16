from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.employee import Employee
from app.core.permissions import Permissions, get_permissions_for_groups

async def get_bookable_employees(db: AsyncSession, current_user: Employee) -> List[Employee]:
    """
    Determine which employees the current user can book for based on permissions.
    """
    # Calculate permissions
    user_group_names = [g.name for g in current_user.groups]
    permissions = get_permissions_for_groups(user_group_names)
    
    # 1. Book Anyone (Travel Admin)
    # TODO: Scale this for large orgs (pagination/search instead of list all)
    if Permissions.BOOK_ANYONE in permissions:
        result = await db.execute(select(Employee).where(Employee.org_id == current_user.org_id))
        return result.scalars().all()
        
    # 2. Book for Others (Executive Assistant / Manager)
    # Logic: Can book for people who have assigned this user as a 'delegate' or are in same 'team'
    # For now (MVP): We'll assume EA can book for anyone in their groups.
    # TODO: Implement explicit delegation table
    if Permissions.BOOK_FOR_OTHERS in permissions:
        # Placeholder: Return self + basic team logic (e.g. same group members)
        # For strict MVP: Just return self until delegation table exists
        return [current_user] 

    # 3. Default: Book Self Only
    return [current_user]
