"""
Search Schemas - Request/Response models for flight and hotel search with filters.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class CabinClass(str, Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class PolicyStatus(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"


class SortBy(str, Enum):
    PRICE = "price"
    DURATION = "duration"
    DEPARTURE = "departure"
    ARRIVAL = "arrival"
    RATING = "rating"


# ==================== Flight Search ====================


class FlightSearchRequest(BaseModel):
    """Request to search for flights with filters."""

    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code")
    destination: str = Field(
        ..., min_length=3, max_length=3, description="Destination airport IATA code"
    )
    departure_date: date
    return_date: date | None = None
    passengers: int = Field(1, ge=1, le=9)
    cabin_class: CabinClass = CabinClass.ECONOMY

    # Filters
    max_price: float | None = Field(None, description="Maximum price filter")
    max_stops: int | None = Field(
        None, ge=0, le=2, description="Maximum number of stops (0=direct)"
    )
    airlines: list[str] | None = Field(None, description="Filter by airline codes")
    refundable_only: bool = Field(False, description="Only show refundable fares")
    max_duration_hours: int | None = Field(None, description="Maximum flight duration in hours")

    # Sorting
    sort_by: SortBy = Field(SortBy.PRICE, description="Sort results by")


class FlightSegment(BaseModel):
    """A single flight segment."""

    departure_airport: str
    departure_city: str
    arrival_airport: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    carrier_code: str
    carrier_name: str
    flight_number: str
    duration_minutes: int


class FlightOffer(BaseModel):
    """A flight offer returned from search."""

    id: str
    supplier: str
    price: float
    currency: str
    duration_minutes: int
    stops: int
    cabin_class: str
    refundable: bool
    segments: list[FlightSegment]

    # Policy tagging
    policy_status: PolicyStatus = PolicyStatus.COMPLIANT
    policy_notes: list[str] = []

    created_at: datetime


class FlightSearchResponse(BaseModel):
    """Response containing flight search results."""

    origin: str
    origin_city: str
    destination: str
    destination_city: str
    departure_date: date
    offers: list[FlightOffer]
    total_results: int
    search_id: str

    # Filter metadata
    filters_applied: dict = {}
    price_range: dict = {}  # min, max prices in results


# ==================== Hotel Search ====================


class HotelSearchRequest(BaseModel):
    """Request to search for hotels with filters."""

    city: str = Field(..., min_length=2, description="City name")
    checkin_date: date
    checkout_date: date | None = None
    guests: int = Field(1, ge=1, le=10)
    rooms: int = Field(1, ge=1, le=5)

    # Filters
    max_price_per_night: float | None = Field(None, description="Maximum price per night")
    min_stars: int | None = Field(None, ge=1, le=5, description="Minimum star rating")
    max_stars: int | None = Field(None, ge=1, le=5, description="Maximum star rating")
    chains: list[str] | None = Field(None, description="Filter by hotel chain codes")
    amenities: list[str] | None = Field(None, description="Required amenities")
    free_cancellation: bool = Field(False, description="Only free cancellation")
    breakfast_included: bool = Field(False, description="Only with breakfast")

    # Sorting
    sort_by: SortBy = Field(SortBy.PRICE, description="Sort results by")


class HotelOffer(BaseModel):
    """A hotel offer returned from search."""

    id: str
    supplier: str
    chain_code: str
    chain_name: str
    hotel_name: str
    stars: int
    hotel_type: str
    city: str
    country: str
    location: str
    price_per_night: float
    total_price: float
    currency: str
    nights: int
    rooms: int
    room_type: str
    amenities: list[str]
    cancellation_policy: str
    checkin_date: str
    checkout_date: str
    rating: float
    review_count: int
    distance_to_center: float

    # Policy tagging
    policy_status: PolicyStatus = PolicyStatus.COMPLIANT
    policy_notes: list[str] = []

    created_at: datetime


class HotelSearchResponse(BaseModel):
    """Response containing hotel search results."""

    city: str
    country: str
    checkin_date: date
    checkout_date: date | None
    offers: list[HotelOffer]
    total_results: int
    search_id: str

    # Filter metadata
    filters_applied: dict = {}
    price_range: dict = {}


# ==================== Autocomplete / Lookup ====================


class AirportInfo(BaseModel):
    """Airport information for autocomplete."""

    code: str
    city: str
    name: str
    country: str
    is_hub: bool = False


class CityInfo(BaseModel):
    """City information for hotel search autocomplete."""

    city: str
    country: str


class AirlineInfo(BaseModel):
    """Airline information."""

    code: str
    name: str


class HotelChainInfo(BaseModel):
    """Hotel chain information."""

    code: str
    name: str
