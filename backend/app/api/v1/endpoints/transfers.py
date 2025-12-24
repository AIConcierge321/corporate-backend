"""
Transfer/Ground Transport API Endpoints

Integrates with AirportTransfer.com Partner API.
Uses mock mode by default, switches to real API when AIRPORT_TRANSFER_API_KEY is set.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List

from app.api import deps
from app.db.session import get_db
from app.models.employee import Employee
from app.core.access_control import AccessControl
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.transfer_service import get_transfer_client
from app.schemas.transfer import (
    AirportSearchResult,
    TransferQuoteRequest, TransferQuoteResponse,
    TransferBookingRequest, TransferBookingResponse,
    TransferBookingDetails,
    CancelReason, TransferCancelRequest, TransferCancelResponse
)

router = APIRouter()


@router.get("/status")
@limiter.limit("60/minute")
async def get_transfer_api_status(request: Request) -> Any:
    """
    Get transfer API status (mock vs real).
    """
    if settings.AIRPORT_TRANSFER_USE_MOCK or not settings.AIRPORT_TRANSFER_API_KEY:
        mode = "MOCK"
        base_url = "mock"
    elif settings.AIRPORT_TRANSFER_USE_SANDBOX:
        mode = "SANDBOX"
        base_url = settings.AIRPORT_TRANSFER_SANDBOX_URL
    else:
        mode = "PRODUCTION"
        base_url = settings.AIRPORT_TRANSFER_BASE_URL
    
    return {
        "provider": "AirportTransfer.com",
        "mode": mode,
        "api_key_configured": bool(settings.AIRPORT_TRANSFER_API_KEY),
        "base_url": base_url
    }


# ==================== Airport Search ====================

@router.get("/airports", response_model=List[AirportSearchResult])
@limiter.limit("30/minute")
async def search_airports(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (airport name, code, or city)"),
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Search airports for autocomplete.
    
    Returns airports matching the query by name, IATA code, or city.
    """
    client = get_transfer_client()
    results = await client.search_airports(q)
    return results


# ==================== Quotes ====================

@router.post("/quotes", response_model=TransferQuoteResponse)
@limiter.limit("20/minute")
async def get_transfer_quotes(
    request: Request,
    request_in: TransferQuoteRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get transfer quotes for a route.
    
    Provide:
    - pickup_location: Airport (IATA code or ID) or Place (Google Place ID)
    - drop_of_location: Airport or Place
    - flight_arrival: When the flight arrives
    - travelers: Number of passengers (adult, children, infant)
    
    Returns available vehicles with pricing.
    """
    # Check booking permission
    ac = AccessControl(current_user)
    if not ac.can("book_ground"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to book ground transport"
        )
    
    try:
        client = get_transfer_client()
        response = await client.get_quotes(
            pickup_location=request_in.pickup_location,
            drop_of_location=request_in.drop_of_location,
            flight_arrival=request_in.flight_arrival,
            travelers=request_in.travelers
        )
        
        # Tag vehicles with policy status based on price
        # (simple rule: expensive luxury vehicles may need approval)
        for vehicle in response.vehicles:
            if "Luxury" in vehicle.segment:
                vehicle.policy_status = "warning"
            else:
                vehicle.policy_status = "compliant"
        
        return response
        
    except Exception as e:
        # MED-001: Log full details server-side, return generic message to client
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Transfer quote search failed: {e}",
            exc_info=True,
            extra={"user_id": current_user.id}
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching for transfers. Please try again or contact support."
        )


# ==================== Booking ====================

@router.post("/book", response_model=TransferBookingResponse)
@limiter.limit("20/minute")
async def create_transfer_booking(
    request: Request,
    request_in: TransferBookingRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a transfer booking.
    
    Requires search_id and vehicle_id from the quotes response.
    """
    # Check booking permission
    ac = AccessControl(current_user)
    if not ac.can("book_ground"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to book ground transport"
        )
    
    try:
        client = get_transfer_client()
        response = await client.create_booking(
            search_id=request_in.search_id,
            vehicle_id=request_in.vehicle_id,
            passenger=request_in.passenger,
            suitcase=request_in.suitcase,
            small_bags=request_in.small_bags,
            travel_details=request_in.travel_details.model_dump() if request_in.travel_details else None
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/booking/{reservation_no}", response_model=TransferBookingDetails)
@limiter.limit("60/minute")
async def get_transfer_booking(
    request: Request,
    reservation_no: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get transfer booking details.
    
    Driver information (name, phone, vehicle plate) will be available
    when booking status is APPROVED.
    
    You can poll this endpoint every 10 minutes to check for driver assignment.
    """
    try:
        client = get_transfer_client()
        booking = await client.get_booking(reservation_no)
        return booking
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Cancellation ====================

@router.get("/cancel-reasons", response_model=List[CancelReason])
@limiter.limit("60/minute")
async def get_cancel_reasons(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get available cancellation reasons.
    
    Use the reason ID when cancelling a booking.
    """
    client = get_transfer_client()
    return await client.get_cancel_reasons()


@router.post("/cancel", response_model=TransferCancelResponse)
@limiter.limit("10/minute")
async def cancel_transfer(
    request: Request,
    request_in: TransferCancelRequest,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Cancel a transfer booking.
    
    Requires reservation_no and cancellation_id from cancel-reasons.
    """
    try:
        client = get_transfer_client()
        response = await client.cancel_booking(
            reservation_no=request_in.reservation_no,
            cancellation_id=request_in.cancellation_id
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
