"""
Transfer/Ground Transport Schemas

For AirportTransfer.com Partner API integration.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


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
    """Location for pickup or dropoff."""
    location_id: str | int = Field(..., description="Airport ID, IATA code, or Google Place ID")
    type: LocationType
    name: Optional[str] = None  # For display
    lat: Optional[float] = None  # For coordinates
    lng: Optional[float] = None


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
                "travelers": {"adult": 2, "children": 1, "infant": 0}
            }
        }


class VehicleCompany(BaseModel):
    """Transfer company information."""
    name: str
    rating: Optional[float] = None
    review_count: Optional[int] = None


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
    company: Optional[VehicleCompany] = None
    
    # Policy tagging
    policy_status: Optional[str] = None  # compliant, warning, violation


class QuoteAirport(BaseModel):
    """Airport info in quote response."""
    id: int
    name: str
    code: str


class TransferQuoteResponse(BaseModel):
    """Response with available transfer vehicles."""
    search_id: str
    airport: QuoteAirport
    vehicles: List[Vehicle]
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
    flight_number: Optional[str] = None


class TravelDetails(BaseModel):
    """Additional travel details."""
    airlines: Optional[str] = None
    extra_requests: Optional[str] = None
    return_airline: Optional[str] = None
    return_flight_number: Optional[str] = None


class TransferBookingRequest(BaseModel):
    """Request to create a transfer booking."""
    search_id: str = Field(..., description="searchID from quote response")
    vehicle_id: str = Field(..., description="Vehicle ID from quote response")
    passenger: PassengerInfo
    suitcase: int = Field(default=0, ge=0)
    small_bags: int = Field(default=0, ge=0)
    travel_details: Optional[TravelDetails] = None
    
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
                    "flight_number": "BA123"
                },
                "suitcase": 2,
                "small_bags": 1
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
    name: Optional[str] = None
    phone: Optional[str] = None
    vehicle_plate: Optional[str] = None


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
    driver: Optional[DriverInfo] = None
    travelers: Travelers
    price: BookingPrice
    vehicle: Vehicle
    distance: float
    booking_type: str = "ONEWAY"
    is_cancelable: bool
    created_at: datetime
    payment_type: Optional[str] = None


# ==================== Cancellation ====================

class CancelReason(BaseModel):
    """Cancellation reason."""
    id: int
    cancellation_name: str
    cancellation_description: Optional[str] = None


class TransferCancelRequest(BaseModel):
    """Request to cancel a transfer."""
    reservation_no: str
    cancellation_id: int


class TransferCancelResponse(BaseModel):
    """Response after cancellation."""
    status: str
    message: str
    refund_amount: Optional[float] = None
