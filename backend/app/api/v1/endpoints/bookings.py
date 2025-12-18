from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any, Optional
from datetime import datetime
import uuid

from app.api import deps
from app.api.auth_deps import require_permissions
from app.core.permissions import Permissions
from app.db.session import get_db
from app.models.booking import Booking, BookingTraveler, BookingStatus
from app.models.employee import Employee
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import get_bookable_employees

router = APIRouter()

@router.post("/draft", response_model=BookingResponse)
async def create_booking_draft(
    booking_in: BookingCreate,
    current_user: Employee = Depends(require_permissions({Permissions.BOOK_SELF})),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new draft booking.
    Enforces 'Book-for' logic.
    """
    # 1. Validate 'Book-for' permissions
    allowed_travelers = await get_bookable_employees(db, current_user)
    allowed_ids = {t.id for t in allowed_travelers}
    
    
    # Check if we are booking for someone we are allowed to
    requesting_ids = set(booking_in.traveler_ids)
    if not requesting_ids.issubset(allowed_ids):
         raise HTTPException(
            status_code=403, 
            detail="You are not authorized to book for one or more of these travelers."
        )

    # 2. Fetch traveler objects
    result = await db.execute(select(Employee).where(Employee.id.in_(booking_in.traveler_ids)))
    travelers = result.scalars().all()
    
    if len(travelers) != len(requesting_ids):
        raise HTTPException(status_code=404, detail="One or more travelers not found.")

    # 3. Create Draft
    from app.models.booking import BookingTraveler, TravelerRole
    
    # Assume first traveler is Primary (or logic based on booker)
    assoc_travelers = []
    for idx, t in enumerate(travelers):
        role = TravelerRole.PRIMARY if idx == 0 else TravelerRole.ADDITIONAL
        assoc_travelers.append(BookingTraveler(employee_id=t.id, role=role))
    
    booking = Booking(
        org_id=current_user.org_id,
        booker_id=current_user.id,
        booker_id=current_user.id,
        status="draft",
        trip_name=booking_in.trip_name,
        travelers_association=assoc_travelers
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    # Manually construct response to handle traveler_ids
    return BookingResponse(
        id=booking.id,
        status=booking.status,
        booker_id=booking.booker_id,
        traveler_ids=[t.id for t in travelers], # Use local var
        created_at=booking.created_at,
        trip_name=booking.trip_name
    )

@router.get("/", response_model=List[BookingResponse])
async def list_bookings(
    status: Optional[BookingStatus] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    traveler_id: Optional[int] = None,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List bookings based on visibility permissions and filters.
    """
    from app.core.permissions import get_permissions_for_groups
    perms = get_permissions_for_groups([g.name for g in current_user.groups])
    
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(Booking.org_id == current_user.org_id)
    
    # Permissions
    if Permissions.VIEW_ALL_BOOKINGS in perms:
        pass 
    elif Permissions.VIEW_TEAM_BOOKINGS in perms:
        # Created by me, OR I am traveler, OR created by my subordinates (if Manager)
        stmt = stmt.where((Booking.booker_id == current_user.id) | (Booking.travelers.any(Employee.id == current_user.id)))
    elif Permissions.VIEW_SELF_BOOKINGS in perms:
        stmt = stmt.where((Booking.booker_id == current_user.id) | (Booking.travelers.any(Employee.id == current_user.id)))
    else:
        return []

    # Filters
    if status:
        stmt = stmt.where(Booking.status == status)
    
    if from_date:
        stmt = stmt.where(Booking.created_at >= from_date)
        
    if to_date:
        stmt = stmt.where(Booking.created_at <= to_date)
        
    if traveler_id:
        # Ensure user has permission to view this traveler's bookings if restricted?
        # For now, apply filter on top of base constraints.
        stmt = stmt.where(Booking.travelers.any(Employee.id == traveler_id))

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # Check ownership
    if booking.org_id != current_user.org_id:
         raise HTTPException(status_code=404, detail="Booking not found")

    # Granular Permissions Check
    from app.core.permissions import get_permissions_for_groups
    perms = get_permissions_for_groups([g.name for g in current_user.groups])
    
    is_owner = booking.booker_id == current_user.id
    is_traveler = any(t.id == current_user.id for t in booking.travelers)
    is_admin = Permissions.VIEW_ALL_BOOKINGS in perms
    
    # Manager check (simplistic: is manager of booker?)
    # For now, if VIEW_TEAM_BOOKINGS, we need to check relationship.
    # To keep it efficient, let's assume if they have VIEW_TEAM_BOOKINGS, 
    # we need to query if they manage the booker.
    can_view_team = Permissions.VIEW_TEAM_BOOKINGS in perms
    is_manager = False
    
    if can_view_team and not (is_owner or is_traveler or is_admin):
        # Fetch booker to check manager
        booker_stmt = select(Employee).where(Employee.id == booking.booker_id)
        booker_res = await db.execute(booker_stmt)
        booker = booker_res.scalars().first()
        if booker and booker.manager_id == current_user.id:
            is_manager = True

    if not (is_owner or is_traveler or is_admin or is_manager):
         raise HTTPException(status_code=403, detail="Not authorized to view this booking")

    return booking

@router.post("/{booking_id}/submit", response_model=BookingResponse)
async def submit_booking(
    booking_id: uuid.UUID,
    current_user: Employee = Depends(deps.get_current_user), # Any employee? Should check ownership
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Submit a draft booking for approval/confirmation.
    Runs Policy Engine -> Updates State.
    """
    # 1. Fetch Booking
    stmt = select(Booking).options(selectinload(Booking.travelers_association).joinedload(BookingTraveler.employee)).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.booker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this booking")
        
    # 2. Run Policy Rules
    # 2. Run Policy Rules
    travelers_list = [assoc.employee for assoc in booking.travelers_association]
    
    from app.services.policy_engine import PolicyEngine
    policy_result = PolicyEngine.evaluate(booking, travelers_list)
    
    # 3. State Machine Transition
    from app.services.booking_workflow import BookingStateMachine
    updated_booking = await BookingStateMachine.submit_draft(db, booking, policy_result)
    
    # 4. Construct response
    return BookingResponse(
        id=updated_booking.id,
        status=updated_booking.status,
        booker_id=updated_booking.booker_id,
        traveler_ids=[t.id for t in travelers_list],
        created_at=updated_booking.created_at,
        trip_name=updated_booking.trip_name
    )
