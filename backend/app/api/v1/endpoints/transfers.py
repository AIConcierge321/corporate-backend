"""
Transfer/Ground Transport API Endpoints

Integrates with AirportTransfer.com Partner API.
Uses mock mode by default, switches to real API when AIRPORT_TRANSFER_API_KEY is set.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List

from app.api import deps
from app.db.session import get_db
from app.models.employee import Employee
from app.core.access_control import AccessControl
from app.core.config import settings
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
async def get_transfer_api_status() -> Any:
    """
    Get transfer API status (mock vs real).
    """
    using_real = not settings.AIRPORT_TRANSFER_USE_MOCK and settings.AIRPORT_TRANSFER_API_KEY
    return {
        "mode": "LIVE" if using_real else "MOCK",
        "api_key_configured": bool(settings.AIRPORT_TRANSFER_API_KEY),
        "base_url": settings.AIRPORT_TRANSFER_BASE_URL if using_real else "mock"
    }


# ==================== Airport Search ====================

@router.get("/airports", response_model=List[AirportSearchResult])
async def search_airports(
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
async def get_transfer_quotes(
    request: TransferQuoteRequest,
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
            pickup_location=request.pickup_location,
            drop_of_location=request.drop_of_location,
            flight_arrival=request.flight_arrival,
            travelers=request.travelers
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
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Booking ====================

@router.post("/book", response_model=TransferBookingResponse)
async def create_transfer_booking(
    request: TransferBookingRequest,
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
            search_id=request.search_id,
            vehicle_id=request.vehicle_id,
            passenger=request.passenger,
            suitcase=request.suitcase,
            small_bags=request.small_bags,
            travel_details=request.travel_details.model_dump() if request.travel_details else None
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/booking/{reservation_no}", response_model=TransferBookingDetails)
async def get_transfer_booking(
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
async def get_cancel_reasons(
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get available cancellation reasons.
    
    Use the reason ID when cancelling a booking.
    """
    client = get_transfer_client()
    return await client.get_cancel_reasons()


@router.post("/cancel", response_model=TransferCancelResponse)
async def cancel_transfer(
    request: TransferCancelRequest,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Cancel a transfer booking.
    
    Requires reservation_no and cancellation_id from cancel-reasons.
    """
    try:
        client = get_transfer_client()
        response = await client.cancel_booking(
            reservation_no=request.reservation_no,
            cancellation_id=request.cancellation_id
        )
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
