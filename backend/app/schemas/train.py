"""
Train/Rail Booking Schemas

For All Aboard train API integration (GraphQL).
Docs: https://docs.allaboard.eu/
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

# ==================== Enums ====================


class PassengerType(str, Enum):
    """Passenger age category."""

    ADULT = "ADULT"  # 28-59 years
    YOUTH = "YOUTH"  # 0-27 years
    SENIOR = "SENIOR"  # 60+ years


class ServiceClass(str, Enum):
    """Train service class."""

    BASIC = "BASIC"  # Economy
    STANDARD = "STANDARD"  # Standard
    HIGH = "HIGH"  # First Class
    BEST = "BEST"  # Premium/Business


class Flexibility(str, Enum):
    """Ticket flexibility."""

    NON_FLEX = "NON_FLEX"  # Non-refundable
    SEMI_FLEX = "SEMI_FLEX"  # Partial refund
    FULL_FLEX = "FULL_FLEX"  # Fully flexible


class JourneyType(str, Enum):
    """Type of journey search."""

    SMART = "SMART"  # Comfort-optimized (default)
    NON_STOP = "NON_STOP"  # Fastest/direct
    BLUEPRINT = "BLUEPRINT"  # Predefined routes


class BookingStatus(str, Enum):
    """Booking status."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    TICKETED = "TICKETED"


class OrderStatus(str, Enum):
    """Order status."""

    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


# ==================== Station Search ====================


class StationSearchRequest(BaseModel):
    """Request to search for train stations."""

    query: str = Field(..., min_length=2, description="Station name or city")


class Station(BaseModel):
    """Train station."""

    uid: str
    name: str
    country: str | None = None
    city: str | None = None
    timezone: str | None = None


class StationSearchResponse(BaseModel):
    """List of matching stations."""

    stations: list[Station]
    total: int


# ==================== Passenger ====================


class PassengerInput(BaseModel):
    """Passenger placeholder for search."""

    type: PassengerType = PassengerType.ADULT
    age: int | None = None  # Required for YOUTH/SENIOR
    birth_date: date | None = None


class PassengerDetails(BaseModel):
    """Full passenger details for booking."""

    type: PassengerType
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    is_contact_person: bool = False  # One must be True


# ==================== Journey Search ====================


class TrainSearchRequest(BaseModel):
    """Request to search for train journeys."""

    origin: str = Field(..., description="Origin station UID")
    destination: str = Field(..., description="Destination station UID")
    departure_date: date
    passengers: list[PassengerInput] = Field(default_factory=lambda: [PassengerInput()])
    journey_type: JourneyType = JourneyType.SMART

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "urn:trainline:generic:loc:st8796",
                "destination": "urn:trainline:generic:loc:st4916",
                "departure_date": "2025-02-15",
                "passengers": [{"type": "ADULT"}],
            }
        }


class StationTime(BaseModel):
    """Station with arrival/departure time."""

    station: Station
    time: datetime
    platform: str | None = None


class JourneyLeg(BaseModel):
    """Single leg of a journey."""

    departure: StationTime
    arrival: StationTime
    operator: str
    train_number: str | None = None
    duration_minutes: int


class Journey(BaseModel):
    """Train journey (route option)."""

    uid: str
    departure: datetime
    arrival: datetime
    duration_minutes: int
    changes: int  # Number of transfers
    operators: list[str]
    legs: list[JourneyLeg] | None = None

    # Policy tagging
    policy_status: str | None = None


class TrainSearchResponse(BaseModel):
    """List of available train journeys."""

    journeys: list[Journey]
    origin: Station
    destination: Station
    search_date: date
    total_results: int


# ==================== Offers ====================


class OfferRequest(BaseModel):
    """Request for journey offers/pricing."""

    journey_uid: str
    passengers: list[PassengerInput]
    currency: str = "EUR"


class Price(BaseModel):
    """Price information."""

    amount: float
    currency: str = "EUR"


class Offer(BaseModel):
    """Available offer for a journey."""

    uid: str
    price: Price
    service_class: ServiceClass
    flexibility: Flexibility
    operator: str
    conditions: str | None = None

    # Policy tagging
    policy_status: str | None = None


class OfferResponse(BaseModel):
    """Available offers for a journey."""

    journey_uid: str
    offers: list[Offer]
    requirements: list[str] | None = None  # Required passenger fields


# ==================== Booking ====================


class CreateBookingRequest(BaseModel):
    """Request to create a train booking."""

    offer_uid: str
    journey_uid: str


class UpdateBookingRequest(BaseModel):
    """Request to update booking with passenger details."""

    passengers: list[PassengerDetails]
    selections: list[str] | None = None  # Selected offer UIDs per segment


class Booking(BaseModel):
    """Train booking."""

    uid: str
    status: BookingStatus
    journey: Journey
    offer: Offer
    passengers: list[PassengerDetails] | None = None
    requirements: list[str] | None = None
    created_at: datetime


# ==================== Order ====================


class CreateOrderRequest(BaseModel):
    """Request to create order from booking."""

    booking_uid: str


class Ticket(BaseModel):
    """Issued ticket."""

    uid: str
    pdf_url: str | None = None
    checkin_url: str | None = None
    reference: str | None = None


class Order(BaseModel):
    """Finalized order with tickets."""

    uid: str
    status: OrderStatus
    booking_uid: str
    total_price: Price
    tickets: list[Ticket] | None = None
    created_at: datetime
    confirmed_at: datetime | None = None
