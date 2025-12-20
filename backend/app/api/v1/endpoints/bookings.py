"""
Booking API Endpoints

Supports:
- Create draft bookings
- List bookings with role-based visibility
- Submit for approval
- View individual bookings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any, Optional
from datetime import datetime
import uuid

from app.api import deps
from app.db.session import get_db
from app.models.booking import Booking, BookingTraveler, BookingStatus, TravelerRole
from app.models.employee import Employee
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import get_bookable_employees, check_can_book_for
from app.core.access_control import AccessControl, get_accessible_employee_ids_with_groups

router = APIRouter()


@router.post("/draft", response_model=BookingResponse)
async def create_booking_draft(
    booking_in: BookingCreate,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new draft booking.
    
    Uses role-based access control to validate booking-for permissions.
    """
    # 1. Check AccessControl
    ac = AccessControl(current_user)
    
    # Check if user has any booking permission
    can_book = ac.can("book_flights") or ac.can("book_hotels") or ac.can("book_ground")
    if not can_book:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to create bookings"
        )
    
    # 2. Validate 'Book-for' permissions using role-based access
    allowed = await check_can_book_for(db, current_user, booking_in.traveler_ids)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to book for one or more of these travelers."
        )

    # 3. Fetch traveler objects
    result = await db.execute(select(Employee).where(Employee.id.in_(booking_in.traveler_ids)))
    travelers = result.scalars().all()
    
    if len(travelers) != len(booking_in.traveler_ids):
        raise HTTPException(status_code=404, detail="One or more travelers not found.")

    # 4. Create Draft
    assoc_travelers = []
    for idx, t in enumerate(travelers):
        role = TravelerRole.PRIMARY if idx == 0 else TravelerRole.ADDITIONAL
        assoc_travelers.append(BookingTraveler(employee_id=t.id, role=role))
    
    booking = Booking(
        org_id=current_user.org_id,
        booker_id=current_user.id,
        status="draft",
        trip_name=booking_in.trip_name,
        total_amount=booking_in.total_amount,
        start_date=booking_in.start_date,
        travel_class=booking_in.travel_class,
        travelers_association=assoc_travelers
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    return BookingResponse(
        id=booking.id,
        status=booking.status,
        booker_id=booking.booker_id,
        traveler_ids=[t.id for t in travelers],
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
    List bookings based on role-based visibility permissions.
    
    Visibility is determined by:
    - view_own_bookings: Only own bookings
    - view_team_bookings: Team/subordinate bookings
    - view_all_bookings: All org bookings
    """
    ac = AccessControl(current_user)
    
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(
        Booking.org_id == current_user.org_id
    )
    
    # Role-based visibility
    if ac.can("view_all_bookings"):
        # Admin: no filter needed
        pass
    elif ac.can("view_team_bookings"):
        # Manager: can see team bookings based on access scope
        accessible_ids = await get_accessible_employee_ids_with_groups(db, ac, current_user.org_id)
        if accessible_ids:
            stmt = stmt.where(
                (Booking.booker_id.in_(accessible_ids)) |
                (Booking.travelers.any(Employee.id.in_(accessible_ids)))
            )
    else:
        # Regular employee: only own bookings
        stmt = stmt.where(
            (Booking.booker_id == current_user.id) |
            (Booking.travelers.any(Employee.id == current_user.id))
        )

    # Apply filters
    if status:
        stmt = stmt.where(Booking.status == status)
    
    if from_date:
        stmt = stmt.where(Booking.created_at >= from_date)
        
    if to_date:
        stmt = stmt.where(Booking.created_at <= to_date)
        
    if traveler_id:
        stmt = stmt.where(Booking.travelers.any(Employee.id == traveler_id))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific booking.
    
    Access allowed if:
    - User is the booker
    - User is a traveler
    - User has view_all_bookings permission
    - User has view_team_bookings and booking is within their access scope
    """
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Access check using roles
    ac = AccessControl(current_user)
    
    is_owner = booking.booker_id == current_user.id
    is_traveler = any(t.id == current_user.id for t in booking.travelers)
    has_global_view = ac.can("view_all_bookings")
    
    if is_owner or is_traveler or has_global_view:
        return booking
    
    # Check team visibility
    if ac.can("view_team_bookings"):
        accessible_ids = await get_accessible_employee_ids_with_groups(db, ac, current_user.org_id)
        if accessible_ids is None or booking.booker_id in accessible_ids:
            return booking
        if any(t.id in accessible_ids for t in booking.travelers):
            return booking
    
    raise HTTPException(status_code=403, detail="Not authorized to view this booking")


@router.post("/{booking_id}/submit", response_model=BookingResponse)
async def submit_booking(
    booking_id: uuid.UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Submit a draft booking for approval/confirmation.
    Runs Policy Engine -> Updates State.
    """
    # 1. Fetch Booking
    stmt = select(Booking).options(
        selectinload(Booking.travelers_association).joinedload(BookingTraveler.employee)
    ).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.booker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this booking")
        
    # 2. Run Policy Rules
    travelers_list = [assoc.employee for assoc in booking.travelers_association]
    
    from app.services.policy_engine import PolicyEngine
    policy_result = await PolicyEngine.evaluate(db, booking, travelers_list)
    
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


@router.get("/me/bookable-employees")
async def get_my_bookable_employees(
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get list of employees the current user can book for.
    """
    employees = await get_bookable_employees(db, current_user)
    return [{"id": e.id, "name": e.full_name, "email": e.email} for e in employees]
