"""
Search API Endpoints - Flight and Hotel search with filters, pagination, and caching.

Production-ready features:
- Pagination (configurable page size)
- Redis caching (5-minute TTL for search results)
- Policy compliance tagging
- Proper async patterns
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, Optional
import time
import uuid
import logging

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.api import deps
from app.models.employee import Employee
from app.schemas.search import (
    FlightSearchRequest, FlightSearchResponse,
    HotelSearchRequest, HotelSearchResponse,
    AirportInfo, CityInfo, AirlineInfo, HotelChainInfo,
    FlightOffer, HotelOffer
)
from app.schemas.common import (
    PaginationParams, PaginationMeta, PaginatedSearchResponse, 
    SearchMeta, CacheControl
)
from app.services.search_service import SearchService
from app.services.cache_service import get_cache_service, CacheService
from app.core.rate_limit import limiter


router = APIRouter()


# ==================== Flight Search ====================

class FlightSearchWithPagination(FlightSearchRequest):
    """Flight search request with pagination."""
    page: int = Query(1, ge=1, description="Page number")
    page_size: int = Query(20, ge=1, le=100, description="Results per page")


@router.post("/flights", response_model=PaginatedSearchResponse)
@limiter.limit("10/minute")
async def search_flights(
    request: Request,
    request_in: FlightSearchRequest,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for flights with optional filters and pagination.
    
    **Pagination:**
    - page: Page number (1-indexed)
    - page_size: Items per page (1-100, default 20)
    
    **Filters available:**
    - max_price: Maximum total price
    - max_stops: 0 for direct flights only
    - airlines: List of airline codes (e.g., ["UA", "AA"])
    - refundable_only: Only refundable fares
    - max_duration_hours: Maximum flight duration
    
    **Caching:**
    - Results are cached for 5 minutes
    - Cache key includes search parameters and page
    
    **Results are tagged with policy compliance:**
    - compliant: Within policy limits
    - warning: Exceeds limits but approvable
    - violation: Significantly exceeds limits
    """
    start_time = time.time()
    cache = get_cache_service()
    search_id = str(uuid.uuid4())
    
    # Generate cache key
    cache_key = CacheService.flight_search_key(
        origin=request_in.origin,
        destination=request_in.destination,
        date=str(request_in.departure_date),
        passengers=request_in.passengers,
        cabin=request_in.cabin_class.value,
        page=page
    )
    
    # Check cache first
    cached_result = await cache.get(cache_key)
    cache_control = CacheControl(cached=False, cache_key=cache_key)
    
    if cached_result:
        cache_control = CacheControl(
            cached=True,
            cache_key=cache_key,
            ttl_seconds=CacheService.TTL_MEDIUM
        )
        # Return cached data with updated cache metadata
        cached_result["cache"] = cache_control.model_dump()
        return cached_result
    
    try:
        # Fetch all results from search service
        result = await SearchService.search_flights(db, request, current_user)
        all_offers = result.offers
        total_results = len(all_offers)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_offers = all_offers[start_idx:end_idx]
        
        # Build pagination metadata
        pagination = PaginationMeta.create(
            page=page,
            page_size=page_size,
            total_items=total_results
        )
        
        # Build search metadata
        query_time_ms = int((time.time() - start_time) * 1000)
        search_meta = SearchMeta(
            search_id=search_id,
            query_time_ms=query_time_ms,
            filters_applied=result.filters_applied,
            price_range=result.price_range
        )
        
        # Build response
        response = PaginatedSearchResponse(
            data=[offer.model_dump() for offer in paginated_offers],
            pagination=pagination,
            search=search_meta,
            cache=cache_control
        )
        
        # Cache the result
        await cache.set(cache_key, response.model_dump(), CacheService.TTL_MEDIUM)
        
        return response
        
    except Exception as e:
        # MED-001: Log full details server-side, return generic message to client
        logger.error(
            f"Flight search failed: {e}",
            exc_info=True,
            extra={
                "user_id": current_user.id,
                "origin": request_in.origin,
                "destination": request_in.destination,
                "date": str(request_in.departure_date)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching for flights. Please try again or contact support."
        )


# ==================== Hotel Search ====================

@router.post("/hotels", response_model=PaginatedSearchResponse)
@limiter.limit("10/minute")
async def search_hotels(
    request: Request,
    request_in: HotelSearchRequest,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: Employee = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for hotels with optional filters and pagination.
    
    **Pagination:**
    - page: Page number (1-indexed)
    - page_size: Items per page (1-100, default 20)
    
    **Filters available:**
    - max_price_per_night: Maximum nightly rate
    - min_stars / max_stars: Star rating range
    - chains: Hotel chain codes (e.g., ["HIL", "MAR"])
    - amenities: Required amenities (e.g., ["Free WiFi", "Pool"])
    - free_cancellation: Only free cancellation policies
    - breakfast_included: Only hotels with free breakfast
    
    **Caching:**
    - Results are cached for 5 minutes
    - Cache key includes search parameters and page
    
    **Results are tagged with policy compliance:**
    - compliant: Within policy limits
    - warning: Exceeds limits but approvable  
    - violation: Significantly exceeds limits
    """
    start_time = time.time()
    cache = get_cache_service()
    search_id = str(uuid.uuid4())
    
    # Generate cache key
    checkout = str(request_in.checkout_date) if request_in.checkout_date else "none"
    cache_key = CacheService.hotel_search_key(
        city=request_in.city,
        checkin=str(request_in.checkin_date),
        checkout=checkout,
        guests=request_in.guests,
        rooms=request_in.rooms,
        page=page
    )
    
    # Check cache first
    cached_result = await cache.get(cache_key)
    cache_control = CacheControl(cached=False, cache_key=cache_key)
    
    if cached_result:
        cache_control = CacheControl(
            cached=True,
            cache_key=cache_key,
            ttl_seconds=CacheService.TTL_MEDIUM
        )
        cached_result["cache"] = cache_control.model_dump()
        return cached_result
    
    try:
        # Fetch all results from search service
        result = await SearchService.search_hotels(db, request, current_user)
        all_offers = result.offers
        total_results = len(all_offers)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_offers = all_offers[start_idx:end_idx]
        
        # Build pagination metadata
        pagination = PaginationMeta.create(
            page=page,
            page_size=page_size,
            total_items=total_results
        )
        
        # Build search metadata
        query_time_ms = int((time.time() - start_time) * 1000)
        search_meta = SearchMeta(
            search_id=search_id,
            query_time_ms=query_time_ms,
            filters_applied=result.filters_applied,
            price_range=result.price_range
        )
        
        # Build response
        response = PaginatedSearchResponse(
            data=[offer.model_dump() for offer in paginated_offers],
            pagination=pagination,
            search=search_meta,
            cache=cache_control
        )
        
        # Cache the result
        await cache.set(cache_key, response.model_dump(), CacheService.TTL_MEDIUM)
        
        return response
        
    except Exception as e:
        # MED-001: Log full details server-side, return generic message to client
        logger.error(
            f"Hotel search failed: {e}",
            exc_info=True,
            extra={
                "user_id": current_user.id,
                "city": request_in.city,
                "checkin": str(request_in.checkin_date),
                "guests": request_in.guests
            }
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching for hotels. Please try again or contact support."
        )


# ==================== Autocomplete / Lookup ====================

@router.get("/airports", response_model=List[AirportInfo])
@limiter.limit("30/minute")
async def search_airports(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (city, airport code, or name)"),
    hubs_only: bool = Query(False, description="Only show business hub airports"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
) -> Any:
    """
    Search airports for flight search autocomplete.
    
    **Caching:**
    - Results are cached for 1 hour (static data)
    
    Supports searching by:
    - Airport code (e.g., "JFK", "LAX")
    - City name (e.g., "New York", "London")
    - Airport name (e.g., "Heathrow", "O'Hare")
    """
    cache = get_cache_service()
    cache_key = CacheService.airport_search_key(q)
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached[:limit]
    
    from app.services.suppliers.mock_flight_client import search_airports as mock_search
    
    results = mock_search(q, business_hubs_only=hubs_only)
    airport_infos = [AirportInfo(**r) for r in results]
    
    # Cache for 1 hour (airports rarely change)
    await cache.set(cache_key, [a.model_dump() for a in airport_infos], CacheService.TTL_LONG)
    
    return airport_infos[:limit]


@router.get("/cities", response_model=List[CityInfo])
@limiter.limit("30/minute")
async def search_cities(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (city name)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
) -> Any:
    """
    Search cities for hotel search autocomplete.
    
    **Caching:**
    - Results are cached for 1 hour (static data)
    """
    cache = get_cache_service()
    cache_key = f"{CacheService.PREFIX_STATIC}cities:{q.lower()}"
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached[:limit]
    
    from app.services.suppliers.mock_hotel_client import search_cities as mock_search
    
    results = mock_search(q)
    city_infos = [CityInfo(**r) for r in results]
    
    # Cache for 1 hour
    await cache.set(cache_key, [c.model_dump() for c in city_infos], CacheService.TTL_LONG)
    
    return city_infos[:limit]


@router.get("/airlines", response_model=List[AirlineInfo])
@limiter.limit("60/minute")
async def list_airlines(request: Request) -> Any:
    """
    List all available airlines for filtering.
    
    **Caching:**
    - Results are cached for 24 hours (very static data)
    """
    cache = get_cache_service()
    cache_key = f"{CacheService.PREFIX_STATIC}airlines:all"
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    from app.services.suppliers.mock_flight_client import AIRLINES
    
    results = [AirlineInfo(**a) for a in AIRLINES]
    
    # Cache for 24 hours
    await cache.set(cache_key, [a.model_dump() for a in results], CacheService.TTL_VERY_LONG)
    
    return results


@router.get("/hotel-chains", response_model=List[HotelChainInfo])
@limiter.limit("60/minute")
async def list_hotel_chains(request: Request) -> Any:
    """
    List all available hotel chains for filtering.
    
    **Caching:**
    - Results are cached for 24 hours (very static data)
    """
    cache = get_cache_service()
    cache_key = f"{CacheService.PREFIX_STATIC}hotel_chains:all"
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    from app.services.suppliers.mock_hotel_client import HOTEL_CHAINS
    
    results = [HotelChainInfo(**c) for c in HOTEL_CHAINS]
    
    # Cache for 24 hours
    await cache.set(cache_key, [c.model_dump() for c in results], CacheService.TTL_VERY_LONG)
    
    return results


@router.get("/amenities", response_model=List[str])
@limiter.limit("60/minute")
async def list_amenities(request: Request) -> Any:
    """
    List all available hotel amenities for filtering.
    
    **Caching:**
    - Results are cached for 24 hours (very static data)
    """
    cache = get_cache_service()
    cache_key = f"{CacheService.PREFIX_STATIC}amenities:all"
    
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    from app.services.suppliers.mock_hotel_client import AMENITIES
    
    # Cache for 24 hours
    await cache.set(cache_key, AMENITIES, CacheService.TTL_VERY_LONG)
    
    return AMENITIES


# ==================== Cache Management ====================

@router.delete("/cache", include_in_schema=False)
@limiter.limit("5/minute")
async def clear_search_cache(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user)
) -> Any:
    """
    Clear all search caches (admin only).
    """
    # TODO: Add admin role check
    cache = get_cache_service()
    
    deleted = await cache.delete_pattern(f"{CacheService.PREFIX_SEARCH}*")
    
    return {
        "message": f"Cleared {deleted} search cache entries",
        "deleted_count": deleted
    }
