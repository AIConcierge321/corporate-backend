from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any
import uuid

from app.api import deps
from app.api.auth_deps import require_permissions
from app.core.permissions import Permissions
from app.db.session import get_db
from app.models.booking import Booking
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
    # If booking for others, need extra permission check? 
    # Logic: if current_user in travelers and only self -> OK.
    # If other people -> Permission check implicit in get_bookable_employees logic? 
    # Actually, we should check if requesting `traveler_ids` are in `allowed_ids`.
    
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
    booking = Booking(
        org_id=current_user.org_id,
        booker_id=current_user.id,
        status="draft",
        trip_name=booking_in.trip_name,
        travelers=travelers
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    # Manually construct response to handle traveler_ids
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
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List bookings based on visibility permissions.
    """
    from app.core.permissions import get_permissions_for_groups
    perms = get_permissions_for_groups([g.name for g in current_user.groups])
    
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(Booking.org_id == current_user.org_id)
    
    if Permissions.VIEW_ALL_BOOKINGS in perms:
        # See everything
        pass 
    elif Permissions.VIEW_TEAM_BOOKINGS in perms:
        # TODO: Implement team logic. For now, Bookings I created OR I am traveler
        stmt = stmt.where((Booking.booker_id == current_user.id) | (Booking.travelers.any(Employee.id == current_user.id)))
    elif Permissions.VIEW_SELF_BOOKINGS in perms:
        # Only my bookings
        stmt = stmt.where((Booking.booker_id == current_user.id) | (Booking.travelers.any(Employee.id == current_user.id)))
    else:
        return []

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: uuid.UUID,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # TODO: Add specific permission checks for single resource
    stmt = select(Booking).options(selectinload(Booking.travelers)).where(Booking.id == booking_id)
    result = await db.execute(stmt)
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    # Check ownership
    if booking.org_id != current_user.org_id:
         raise HTTPException(status_code=404, detail="Booking not found")

    return booking
