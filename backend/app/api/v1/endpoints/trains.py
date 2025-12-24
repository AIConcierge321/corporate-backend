"""
Train/Rail Booking API Endpoints

Integrates with All Aboard European rail booking API (GraphQL).
Docs: https://docs.allaboard.eu/
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List

from app.api import deps
from app.db.session import get_db
from app.models.employee import Employee
from app.core.access_control import AccessControl
from app.core.config import settings
from app.services.suppliers.allaboard_client import get_allaboard_client, AllAboardAPIError
from app.schemas.train import (
    StationSearchResponse, Station,
    TrainSearchRequest, TrainSearchResponse,
    OfferRequest, OfferResponse,
    CreateBookingRequest, UpdateBookingRequest, Booking,
    CreateOrderRequest, Order,
    PassengerInput, PassengerDetails
)
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/status")
@limiter.limit("60/minute")
async def get_train_api_status(request: Request) -> Any:
    """
    Get train API status (test vs production).
    """
    return {
        "provider": "All Aboard",
        "mode": "TEST" if settings.ALLABOARD_USE_TEST else "PRODUCTION",
        "api_key_configured": bool(settings.ALLABOARD_API_KEY),
        "base_url": "test.api-gateway.allaboard.eu" if settings.ALLABOARD_USE_TEST else settings.ALLABOARD_BASE_URL
    }


# ==================== Station Search ====================

@router.get("/stations", response_model=StationSearchResponse)
@limiter.limit("60/minute")
async def search_stations(
    request: Request,
    q: str = Query(..., min_length=2, description="Station name or city"),
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Search for train stations by name or city.
    
    Returns matching stations with UIDs for use in journey search.
    """
    try:
        client = get_allaboard_client()
        response = await client.search_stations(q)
        return response
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Journey Search ====================

@router.post("/search", response_model=TrainSearchResponse)
@limiter.limit("20/minute")
async def search_journeys(
    request: Request,
    request_in: TrainSearchRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Search for train journeys between two stations.
    
    Provide:
    - origin: Station UID (from /stations search)
    - destination: Station UID
    - departure_date: Date of travel
    - passengers: List of passenger types (ADULT, YOUTH, SENIOR)
    
    Returns available train connections.
    """
    try:
        client = get_allaboard_client()
        response = await client.search_journeys(
            origin=request_in.origin,
            destination=request_in.destination,
            departure_date=request_in.departure_date,
            passengers=request_in.passengers
        )
        
        # Tag journeys with policy status
        ac = AccessControl(current_user)
        for journey in response.journeys:
            # Simple policy: more than 2 changes may need approval
            if journey.changes > 2:
                journey.policy_status = "warning"
            else:
                journey.policy_status = "compliant"
        
        return response
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Offers ====================

@router.post("/offers", response_model=OfferResponse)
@limiter.limit("20/minute")
async def get_journey_offers(
    request: Request,
    request_in: OfferRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get offers/pricing for a specific journey.
    
    Returns available ticket options with prices and conditions.
    """
    try:
        client = get_allaboard_client()
        response = await client.get_journey_offers(
            journey_uid=request_in.journey_uid,
            passengers=request_in.passengers,
            currency=request_in.currency
        )
        
        # Tag offers with policy status based on class
        ac = AccessControl(current_user)
        for offer in response.offers:
            # Check travel class eligibility
            if offer.service_class.value in ["HIGH", "BEST"]:
                if ac.can("first_class") or ac.can("business_class"):
                    offer.policy_status = "compliant"
                else:
                    offer.policy_status = "violation"
            else:
                offer.policy_status = "compliant"
        
        return response
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Booking ====================

@router.post("/book", response_model=Booking)
@limiter.limit("20/minute")
async def create_booking(
    request: Request,
    request_in: CreateBookingRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a train booking from an offer.
    
    Returns a booking with UID and required passenger fields.
    """
    ac = AccessControl(current_user)
    
    # Check permission (reuse book_flights or add book_trains)
    if not (ac.can("book_flights") or ac.can("book_ground")):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to book train travel"
        )
    
    try:
        client = get_allaboard_client()
        booking = await client.create_booking(request_in.offer_uid)
        return booking
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.put("/booking/{booking_uid}", response_model=Booking)
@limiter.limit("20/minute")
async def update_booking(
    request: Request,
    booking_uid: str,
    request_in: UpdateBookingRequest,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Update booking with passenger details.
    
    One passenger must have isContactPerson=true with email and phone.
    """
    try:
        client = get_allaboard_client()
        booking = await client.update_booking(booking_uid, request_in.passengers)
        return booking
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Order ====================

@router.post("/booking/{booking_uid}/confirm", response_model=Order)
@limiter.limit("20/minute")
async def create_order(
    request: Request,
    booking_uid: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Create an order (pre-book/hold tickets).
    
    This reserves the tickets but doesn't issue them yet.
    """
    try:
        client = get_allaboard_client()
        order = await client.create_order(booking_uid)
        return order
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/order/{order_uid}/finalize", response_model=Order)
@limiter.limit("10/minute")
async def finalize_order(
    request: Request,
    order_uid: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Finalize order and issue tickets.
    
    Returns the order with ticket PDFs and check-in URLs.
    """
    try:
        client = get_allaboard_client()
        order = await client.finalize_order(order_uid)
        return order
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/order/{order_uid}", response_model=Order)
@limiter.limit("60/minute")
async def get_order(
    request: Request,
    order_uid: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get order details and ticket status.
    """
    try:
        client = get_allaboard_client()
        order = await client.get_order(order_uid)
        return order
        
    except AllAboardAPIError as e:
        raise HTTPException(status_code=404, detail=e.message)
