"""
Search API Endpoints - Flight and Hotel search with filters and autocomplete.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, Optional

from app.db.session import get_db
from app.api import deps
from app.models.employee import Employee
from app.schemas.search import (
    FlightSearchRequest, FlightSearchResponse,
    HotelSearchRequest, HotelSearchResponse,
    AirportInfo, CityInfo, AirlineInfo, HotelChainInfo
)
from app.services.search_service import SearchService


router = APIRouter()


# ==================== Flight Search ====================

@router.post("/flights", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for flights with optional filters.
    
    **Filters available:**
    - max_price: Maximum total price
    - max_stops: 0 for direct flights only
    - airlines: List of airline codes (e.g., ["UA", "AA"])
    - refundable_only: Only refundable fares
    - max_duration_hours: Maximum flight duration
    
    **Results are tagged with policy compliance:**
    - compliant: Within policy limits
    - warning: Exceeds limits but approvable
    - violation: Significantly exceeds limits
    """
    try:
        result = await SearchService.search_flights(db, request, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ==================== Hotel Search ====================

@router.post("/hotels", response_model=HotelSearchResponse)
async def search_hotels(
    request: HotelSearchRequest,
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for hotels with optional filters.
    
    **Filters available:**
    - max_price_per_night: Maximum nightly rate
    - min_stars / max_stars: Star rating range
    - chains: Hotel chain codes (e.g., ["HIL", "MAR"])
    - amenities: Required amenities (e.g., ["Free WiFi", "Pool"])
    - free_cancellation: Only free cancellation policies
    - breakfast_included: Only hotels with free breakfast
    
    **Results are tagged with policy compliance:**
    - compliant: Within policy limits
    - warning: Exceeds limits but approvable  
    - violation: Significantly exceeds limits
    """
    try:
        result = await SearchService.search_hotels(db, request, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ==================== Autocomplete / Lookup ====================

@router.get("/airports", response_model=List[AirportInfo])
async def search_airports(
    q: str = Query(..., min_length=1, description="Search query (city, airport code, or name)"),
    hubs_only: bool = Query(False, description="Only show business hub airports"),
) -> Any:
    """
    Search airports for flight search autocomplete.
    
    Supports searching by:
    - Airport code (e.g., "JFK", "LAX")
    - City name (e.g., "New York", "London")
    - Airport name (e.g., "Heathrow", "O'Hare")
    """
    from app.services.suppliers.mock_flight_client import search_airports
    
    results = search_airports(q, business_hubs_only=hubs_only)
    return [AirportInfo(**r) for r in results]


@router.get("/cities", response_model=List[CityInfo])
async def search_cities(
    q: str = Query(..., min_length=1, description="Search query (city name)"),
) -> Any:
    """
    Search cities for hotel search autocomplete.
    """
    from app.services.suppliers.mock_hotel_client import search_cities
    
    results = search_cities(q)
    return [CityInfo(**r) for r in results]


@router.get("/airlines", response_model=List[AirlineInfo])
async def list_airlines() -> Any:
    """
    List all available airlines for filtering.
    """
    from app.services.suppliers.mock_flight_client import AIRLINES
    
    return [AirlineInfo(**a) for a in AIRLINES]


@router.get("/hotel-chains", response_model=List[HotelChainInfo])
async def list_hotel_chains() -> Any:
    """
    List all available hotel chains for filtering.
    """
    from app.services.suppliers.mock_hotel_client import HOTEL_CHAINS
    
    return [HotelChainInfo(**c) for c in HOTEL_CHAINS]


@router.get("/amenities", response_model=List[str])
async def list_amenities() -> Any:
    """
    List all available hotel amenities for filtering.
    """
    from app.services.suppliers.mock_hotel_client import AMENITIES
    
    return AMENITIES
