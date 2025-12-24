"""
Transfer/Ground Transport Schemas

For AirportTransfer.com Partner API integration.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ==================== Enums ====================


class LocationType(str, Enum):
    """Type of location for pickup/dropoff."""

    AIRPORT = "AIRPORT"
    PLACE = "PLACE"


class VehicleSegment(str, Enum):
    """Vehicle segment/class."""

    STANDARD_SEDAN = "Standard Sedan"
    PREMIUM_SEDAN = "Premium Sedan"
    STANDARD_SUV = "Standard SUV"
    LUXURY_SEDAN = "Luxury Sedan"
    VAN = "Van"
    MINIBUS = "Minibus"


class TransferStatus(str, Enum):
    """Transfer booking status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ==================== Location ====================


class Location(BaseModel):
    """Location for pickup or dropoff.

    For AIRPORT: use location_id (IATA code like 'AMS')
    For PLACE: use name + lat + lng (GPS coordinates)
    """

    location_id: str | int | None = None  # Airport IATA code or ID
    type: LocationType
    name: str | None = None  # For display (required for PLACE)
    lat: float | None = None  # GPS latitude (required for PLACE)
    lng: float | None = None  # GPS longitude (required for PLACE)


class Travelers(BaseModel):
    """Number of travelers by type."""

    adult: int = Field(..., ge=1)
    children: int = Field(default=0, ge=0)
    infant: int = Field(default=0, ge=0)


# ==================== Airport Search ====================


class AirportSearchResult(BaseModel):
    """Airport from location search."""

    id: int
    name: str
    code: str  # IATA code
    description: str  # City, Country


# ==================== Quotes ====================


class TransferQuoteRequest(BaseModel):
    """Request for transfer quotes."""

    pickup_location: Location
    drop_of_location: Location
    flight_arrival: datetime = Field(..., description="Flight arrival time")
    travelers: Travelers

    class Config:
        json_schema_extra = {
            "example": {
                "pickup_location": {"location_id": "LHR", "type": "AIRPORT"},
                "drop_of_location": {"location_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI", "type": "PLACE"},
                "flight_arrival": "2025-02-15T14:30:00",
                "travelers": {"adult": 2, "children": 1, "infant": 0},
            }
        }


class VehicleCompany(BaseModel):
    """Transfer company information."""

    name: str
    rating: float | None = None
    review_count: int | None = None


class Vehicle(BaseModel):
    """Available vehicle for transfer."""

    id: int
    make: str
    model: str
    segment: str
    type: str
    price: float
    currency: str = "USD"
    min_passengers: int
    max_passengers: int
    suitcase: int  # Max suitcases
    small_bag: int  # Max small bags
    image: str
    company: VehicleCompany | None = None

    # Policy tagging
    policy_status: str | None = None  # compliant, warning, violation


class QuoteAirport(BaseModel):
    """Airport info in quote response."""

    id: int
    name: str
    code: str


class TransferQuoteResponse(BaseModel):
    """Response with available transfer vehicles."""

    search_id: str
    airport: QuoteAirport
    vehicles: list[Vehicle]
    distance: float  # in km
    dealer_count: int
    search_status: str


# ==================== Booking ====================


class PassengerInfo(BaseModel):
    """Passenger/lead traveler information."""

    gender: str = Field(..., pattern="^(Mr|Mrs|Ms)$")
    name: str
    surname: str
    email: str
    phone: str
    flight_number: str | None = None


class TravelDetails(BaseModel):
    """Additional travel details."""

    airlines: str | None = None
    extra_requests: str | None = None
    return_airline: str | None = None
    return_flight_number: str | None = None


class TransferBookingRequest(BaseModel):
    """Request to create a transfer booking."""

    search_id: str = Field(..., description="searchID from quote response")
    vehicle_id: str = Field(..., description="Vehicle ID from quote response")
    passenger: PassengerInfo
    suitcase: int = Field(default=0, ge=0)
    small_bags: int = Field(default=0, ge=0)
    travel_details: TravelDetails | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "search_id": "api_abc123",
                "vehicle_id": "456",
                "passenger": {
                    "gender": "Mr",
                    "name": "John",
                    "surname": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1234567890",
                    "flight_number": "BA123",
                },
                "suitcase": 2,
                "small_bags": 1,
            }
        }


class TransferBookingResponse(BaseModel):
    """Response after creating a booking."""

    status: str
    message: str
    reservation_no: str
    search_id: str


# ==================== Booking Details ====================


class DriverInfo(BaseModel):
    """Driver information (available after APPROVED)."""

    name: str | None = None
    phone: str | None = None
    vehicle_plate: str | None = None


class BookingPrice(BaseModel):
    """Price breakdown."""

    total: float
    currency: str


class TransferBookingDetails(BaseModel):
    """Full booking details."""

    reservation_no: str
    status: TransferStatus
    pickup_location: Location
    drop_of_location: Location
    passenger: PassengerInfo
    driver: DriverInfo | None = None
    travelers: Travelers
    price: BookingPrice
    vehicle: Vehicle
    distance: float
    booking_type: str = "ONEWAY"
    is_cancelable: bool
    created_at: datetime
    payment_type: str | None = None


# ==================== Cancellation ====================


class CancelReason(BaseModel):
    """Cancellation reason."""

    id: int
    cancellation_name: str
    cancellation_description: str | None = None


class TransferCancelRequest(BaseModel):
    """Request to cancel a transfer."""

    reservation_no: str
    cancellation_id: int


class TransferCancelResponse(BaseModel):
    """Response after cancellation."""

    status: str
    message: str
    refund_amount: float | None = None
