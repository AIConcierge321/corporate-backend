"""
Destination Intelligence Schemas
"""

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PresenceType(str, Enum):
    OFFICE = "office"
    ADVISORY = "advisory"
    CLIENT = "client"
    PARTNER = "partner"


class PreferredHotel(BaseModel):
    """A preferred/negotiated hotel property."""

    name: str
    stars: int
    rate: float


class DestinationSummary(BaseModel):
    """Summary view of a destination for list view."""

    id: str
    city: str
    country: str
    country_code: str
    region: str
    presence: PresenceType
    risk_level: RiskLevel
    visa_required: bool

    # Stats
    trips_per_year: int
    active_clients: int
    market_savings_pct: float

    # Averages
    avg_flight_cost: float
    avg_hotel_rate: float
    avg_flight_time_minutes: int

    preferred_hotels: int
    is_hub: bool


class DestinationDetail(DestinationSummary):
    """Full destination details."""

    timezone: str
    currency: str

    # Preferred hotels list
    preferred_hotels_list: list[PreferredHotel]

    # Hub info
    hub_airports: list[str]

    # Quick facts
    language: str
    power_plug: str
    emergency: str


class FrequentRoute(BaseModel):
    """Popular travel route."""

    id: str
    origin: str
    origin_city: str
    destination: str
    destination_city: str
    trips_per_month: int
    avg_price: float
    best_carrier: str
    avg_duration_minutes: int


class DestinationStats(BaseModel):
    """Aggregate destination statistics."""

    active_destinations: int
    preferred_hotels: int
    avg_savings_pct: float
    frequent_routes: int


class DestinationSearchRequest(BaseModel):
    """Request to search destinations."""

    query: str | None = Field(None, description="Search by city or country name")
    region: str | None = Field(None, description="Filter by region")
    hubs_only: bool = Field(False, description="Only show business hubs")


class DestinationSearchResponse(BaseModel):
    """Response with destination search results."""

    destinations: list[DestinationSummary]
    total_results: int
    stats: DestinationStats
    regions: list[str]
