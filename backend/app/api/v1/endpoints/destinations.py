"""
Destination Intelligence API Endpoints

Explore business destinations with:
- Corporate rates and travel insights
- Policy-aware recommendations
- Preferred suppliers and hotels
- Frequent routes
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api import deps
from app.core.rate_limit import limiter
from app.models.employee import Employee
from app.schemas.destination import (
    DestinationDetail,
    DestinationSearchResponse,
    DestinationStats,
    DestinationSummary,
    FrequentRoute,
    PreferredHotel,
)
from app.services.suppliers.destination_data import (
    DESTINATIONS,
    REGIONS,
    get_destination_stats,
    get_frequent_routes,
    search_destinations,
)

router = APIRouter()


@router.get("/", response_model=DestinationSearchResponse)
@limiter.limit("30/minute")
async def list_destinations(
    request: Request,
    q: str | None = Query(None, description="Search query"),
    region: str | None = Query(None, description="Filter by region"),
    hubs_only: bool = Query(False, description="Only business hubs"),
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    List and search destinations with travel intelligence.

    **Filters:**
    - q: Search by city or country name
    - region: Filter by region (Europe, Asia Pacific, etc.)
    - hubs_only: Only show business hub destinations
    """
    results = search_destinations(query=q, region=region, hubs_only=hubs_only)
    stats = get_destination_stats()

    # Convert to summary objects
    destinations = [
        DestinationSummary(
            id=r["id"],
            city=r["city"],
            country=r["country"],
            country_code=r["country_code"],
            region=r["region"],
            presence=r["presence"],
            risk_level=r["risk_level"],
            visa_required=r["visa_required"],
            trips_per_year=r["trips_per_year"],
            active_clients=r["active_clients"],
            market_savings_pct=r["market_savings_pct"],
            avg_flight_cost=r["avg_flight_cost"],
            avg_hotel_rate=r["avg_hotel_rate"],
            avg_flight_time_minutes=r["avg_flight_time_minutes"],
            preferred_hotels=r["preferred_hotels"],
            is_hub=r.get("is_hub", False),
        )
        for r in results
    ]

    return DestinationSearchResponse(
        destinations=destinations,
        total_results=len(destinations),
        stats=DestinationStats(**stats),
        regions=REGIONS,
    )


@router.get("/stats", response_model=DestinationStats)
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get aggregate destination statistics.

    Returns:
    - Active destinations count
    - Total preferred hotels
    - Average savings vs market
    - Number of frequent routes
    """
    stats = get_destination_stats()
    return DestinationStats(**stats)


@router.get("/regions", response_model=list[str])
@limiter.limit("60/minute")
async def list_regions(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    List all available regions for filtering.
    """
    return REGIONS


@router.get("/routes", response_model=list[FrequentRoute])
@limiter.limit("30/minute")
async def list_frequent_routes(
    request: Request,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get frequently traveled routes with insights.

    Shows top routes by volume with:
    - Average price
    - Best carrier
    - Trip frequency
    """
    routes = get_frequent_routes()
    return [FrequentRoute(**r) for r in routes]


@router.get("/{destination_id}", response_model=DestinationDetail)
@limiter.limit("60/minute")
async def get_destination(
    request: Request,
    destination_id: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get detailed destination information.

    Includes:
    - Travel statistics and costs
    - Preferred hotels with negotiated rates
    - Visa requirements and risk level
    - Local information (language, timezone, emergency)
    """
    dest = DESTINATIONS.get(destination_id.lower())

    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    # Build preferred hotels list
    hotels = [PreferredHotel(**h) for h in dest.get("preferred_hotels_list", [])]

    return DestinationDetail(
        id=destination_id.lower(),
        city=dest["city"],
        country=dest["country"],
        country_code=dest["country_code"],
        region=dest["region"],
        timezone=dest["timezone"],
        currency=dest["currency"],
        presence=dest["presence"],
        risk_level=dest["risk_level"],
        visa_required=dest["visa_required"],
        trips_per_year=dest["trips_per_year"],
        active_clients=dest["active_clients"],
        market_savings_pct=dest["market_savings_pct"],
        avg_flight_cost=dest["avg_flight_cost"],
        avg_hotel_rate=dest["avg_hotel_rate"],
        avg_flight_time_minutes=dest["avg_flight_time_minutes"],
        preferred_hotels=dest["preferred_hotels"],
        preferred_hotels_list=hotels,
        is_hub=dest.get("is_hub", False),
        hub_airports=dest.get("hub_airports", []),
        language=dest.get("language", ""),
        power_plug=dest.get("power_plug", ""),
        emergency=dest.get("emergency", ""),
    )


@router.get("/{destination_id}/hotels", response_model=list[PreferredHotel])
@limiter.limit("60/minute")
async def get_destination_hotels(
    request: Request,
    destination_id: str,
    current_user: Employee = Depends(deps.get_current_user),
) -> Any:
    """
    Get preferred hotels for a destination with negotiated rates.
    """
    dest = DESTINATIONS.get(destination_id.lower())

    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")

    hotels = dest.get("preferred_hotels_list", [])
    return [PreferredHotel(**h) for h in hotels]
