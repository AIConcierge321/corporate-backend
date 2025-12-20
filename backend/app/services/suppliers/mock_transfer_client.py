"""
Mock Transfer Client

Generates realistic fake data for ground transport/taxi transfers.
Used for development without AirportTransfer API key.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from app.schemas.transfer import (
    AirportSearchResult, TransferQuoteResponse, QuoteAirport, Vehicle, VehicleCompany,
    TransferBookingResponse, TransferBookingDetails, DriverInfo, BookingPrice,
    CancelReason, TransferCancelResponse, Location, Travelers, PassengerInfo,
    LocationType, TransferStatus
)

# ==================== Mock Data ====================

AIRPORTS = [
    {"id": 8554, "name": "London Heathrow Airport", "code": "LHR", "description": "London, United Kingdom"},
    {"id": 8555, "name": "London Gatwick Airport", "code": "LGW", "description": "London, United Kingdom"},
    {"id": 8556, "name": "London Stansted Airport", "code": "STN", "description": "London, United Kingdom"},
    {"id": 1001, "name": "John F Kennedy International Airport", "code": "JFK", "description": "New York, United States"},
    {"id": 1002, "name": "LaGuardia Airport", "code": "LGA", "description": "New York, United States"},
    {"id": 1003, "name": "Newark Liberty International Airport", "code": "EWR", "description": "Newark, United States"},
    {"id": 2001, "name": "Charles de Gaulle Airport", "code": "CDG", "description": "Paris, France"},
    {"id": 2002, "name": "Paris Orly Airport", "code": "ORY", "description": "Paris, France"},
    {"id": 3001, "name": "Dubai International Airport", "code": "DXB", "description": "Dubai, United Arab Emirates"},
    {"id": 4001, "name": "Singapore Changi Airport", "code": "SIN", "description": "Singapore"},
    {"id": 5001, "name": "Tokyo Narita International Airport", "code": "NRT", "description": "Tokyo, Japan"},
    {"id": 5002, "name": "Tokyo Haneda Airport", "code": "HND", "description": "Tokyo, Japan"},
    {"id": 6001, "name": "Los Angeles International Airport", "code": "LAX", "description": "Los Angeles, United States"},
    {"id": 7001, "name": "San Francisco International Airport", "code": "SFO", "description": "San Francisco, United States"},
    {"id": 8001, "name": "Frankfurt Airport", "code": "FRA", "description": "Frankfurt, Germany"},
]

VEHICLE_TEMPLATES = [
    {
        "segment": "Standard Sedan",
        "type": "Sedan",
        "makes": [("Toyota", "Camry"), ("Honda", "Accord"), ("Volkswagen", "Passat")],
        "base_price": 45,
        "max_passengers": 3,
        "suitcase": 2,
        "small_bag": 2,
        "image": "https://cdn.airporttransfer.com/cars/sedan.jpg"
    },
    {
        "segment": "Premium Sedan",
        "type": "Sedan",
        "makes": [("Mercedes-Benz", "E-Class"), ("BMW", "5 Series"), ("Audi", "A6")],
        "base_price": 75,
        "max_passengers": 3,
        "suitcase": 2,
        "small_bag": 2,
        "image": "https://cdn.airporttransfer.com/cars/premium-sedan.jpg"
    },
    {
        "segment": "Standard SUV",
        "type": "SUV",
        "makes": [("Toyota", "Highlander"), ("Ford", "Explorer"), ("Chevrolet", "Tahoe")],
        "base_price": 65,
        "max_passengers": 5,
        "suitcase": 4,
        "small_bag": 4,
        "image": "https://cdn.airporttransfer.com/cars/suv.jpg"
    },
    {
        "segment": "Luxury Sedan",
        "type": "Sedan",
        "makes": [("Mercedes-Benz", "S-Class"), ("BMW", "7 Series"), ("Audi", "A8")],
        "base_price": 120,
        "max_passengers": 3,
        "suitcase": 2,
        "small_bag": 2,
        "image": "https://cdn.airporttransfer.com/cars/luxury.jpg"
    },
    {
        "segment": "Van",
        "type": "Van",
        "makes": [("Mercedes-Benz", "V-Class"), ("Volkswagen", "Caravelle"), ("Ford", "Transit")],
        "base_price": 85,
        "max_passengers": 7,
        "suitcase": 6,
        "small_bag": 6,
        "image": "https://cdn.airporttransfer.com/cars/van.jpg"
    },
    {
        "segment": "Minibus",
        "type": "Minibus",
        "makes": [("Mercedes-Benz", "Sprinter"), ("Ford", "Transit"), ("Iveco", "Daily")],
        "base_price": 110,
        "max_passengers": 12,
        "suitcase": 12,
        "small_bag": 12,
        "image": "https://cdn.airporttransfer.com/cars/minibus.jpg"
    },
]

COMPANIES = [
    {"name": "Premium Transfers", "rating": 4.8, "review_count": 1250},
    {"name": "City Express", "rating": 4.5, "review_count": 890},
    {"name": "Airport Direct", "rating": 4.7, "review_count": 2100},
    {"name": "Executive Cars", "rating": 4.9, "review_count": 560},
    {"name": "Swift Transfers", "rating": 4.4, "review_count": 1800},
]

CANCEL_REASONS = [
    {"id": 1, "cancellation_name": "Flight cancelled", "cancellation_description": "My flight was cancelled"},
    {"id": 2, "cancellation_name": "Flight delayed", "cancellation_description": "Significant flight delay"},
    {"id": 3, "cancellation_name": "Change of plans", "cancellation_description": "Travel plans changed"},
    {"id": 4, "cancellation_name": "Found alternative", "cancellation_description": "Found another transportation option"},
    {"id": 5, "cancellation_name": "Booking error", "cancellation_description": "Made a booking mistake"},
    {"id": 6, "cancellation_name": "Other", "cancellation_description": "Other reason"},
]

# In-memory storage for mock bookings
_mock_bookings: Dict[str, dict] = {}
_mock_quotes: Dict[str, dict] = {}


class MockTransferClient:
    """
    Mock client for AirportTransfer API.
    Generates realistic fake data for development.
    """
    
    async def search_airports(self, query: str) -> List[AirportSearchResult]:
        """Search airports by name, code, or city."""
        query_lower = query.lower()
        results = []
        
        for airport in AIRPORTS:
            if (query_lower in airport["name"].lower() or
                query_lower in airport["code"].lower() or
                query_lower in airport["description"].lower()):
                results.append(AirportSearchResult(**airport))
        
        return results[:10]  # Limit to 10 results
    
    async def get_quotes(
        self,
        pickup_location: Location,
        drop_of_location: Location,
        flight_arrival: datetime,
        travelers: Travelers
    ) -> TransferQuoteResponse:
        """Get transfer quotes for a route."""
        
        # Generate search ID
        search_id = f"api_{uuid.uuid4().hex[:12]}"
        
        # Find airport info
        airport_info = self._find_airport(pickup_location, drop_of_location)
        
        # Calculate distance (mock: random 15-60 km)
        distance = round(random.uniform(15, 60), 1)
        
        # Generate vehicles
        total_passengers = travelers.adult + travelers.children
        vehicles = self._generate_vehicles(distance, total_passengers)
        
        # Store quote for later booking
        _mock_quotes[search_id] = {
            "pickup_location": pickup_location.model_dump(),
            "drop_of_location": drop_of_location.model_dump(),
            "flight_arrival": flight_arrival.isoformat(),
            "travelers": travelers.model_dump(),
            "vehicles": {str(v.id): v.model_dump() for v in vehicles},
            "airport": airport_info,
            "distance": distance,
        }
        
        return TransferQuoteResponse(
            search_id=search_id,
            airport=QuoteAirport(
                id=airport_info["id"],
                name=airport_info["name"],
                code=airport_info["code"]
            ),
            vehicles=vehicles,
            distance=distance,
            dealer_count=len(COMPANIES),
            search_status="OK"
        )
    
    async def create_booking(
        self,
        search_id: str,
        vehicle_id: str,
        passenger: PassengerInfo,
        suitcase: int = 0,
        small_bags: int = 0,
        travel_details: Optional[dict] = None
    ) -> TransferBookingResponse:
        """Create a transfer booking."""
        
        # Validate search_id
        if search_id not in _mock_quotes:
            raise ValueError("Invalid search_id. Please get a new quote.")
        
        quote = _mock_quotes[search_id]
        
        # Validate vehicle_id
        if vehicle_id not in quote["vehicles"]:
            raise ValueError("Invalid vehicle_id")
        
        vehicle = quote["vehicles"][vehicle_id]
        
        # Generate reservation number
        reservation_no = f"AT-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:3].upper()}"
        
        # Store booking
        _mock_bookings[reservation_no] = {
            "reservation_no": reservation_no,
            "status": TransferStatus.PENDING.value,
            "pickup_location": quote["pickup_location"],
            "drop_of_location": quote["drop_of_location"],
            "passenger": passenger.model_dump(),
            "driver": None,
            "travelers": quote["travelers"],
            "price": {"total": vehicle["price"], "currency": vehicle["currency"]},
            "vehicle": vehicle,
            "distance": quote["distance"],
            "booking_type": "ONEWAY",
            "is_cancelable": True,
            "created_at": datetime.now().isoformat(),
            "suitcase": suitcase,
            "small_bags": small_bags,
        }
        
        return TransferBookingResponse(
            status="Success",
            message="The Booking has been successfully created.",
            reservation_no=reservation_no,
            search_id=search_id
        )
    
    async def get_booking(self, reservation_no: str) -> TransferBookingDetails:
        """Get booking details."""
        
        if reservation_no not in _mock_bookings:
            raise ValueError("Reservation not found")
        
        booking = _mock_bookings[reservation_no]
        
        # Simulate driver assignment after some time
        driver = None
        if booking["status"] == TransferStatus.APPROVED.value:
            driver = DriverInfo(
                name="James Smith",
                phone="+44 7700 900123",
                vehicle_plate="AB12 CDE"
            )
        
        return TransferBookingDetails(
            reservation_no=booking["reservation_no"],
            status=TransferStatus(booking["status"]),
            pickup_location=Location(**booking["pickup_location"]),
            drop_of_location=Location(**booking["drop_of_location"]),
            passenger=PassengerInfo(**booking["passenger"]),
            driver=driver,
            travelers=Travelers(**booking["travelers"]),
            price=BookingPrice(**booking["price"]),
            vehicle=Vehicle(**booking["vehicle"]),
            distance=booking["distance"],
            booking_type=booking["booking_type"],
            is_cancelable=booking["is_cancelable"],
            created_at=datetime.fromisoformat(booking["created_at"])
        )
    
    async def get_cancel_reasons(self) -> List[CancelReason]:
        """Get available cancellation reasons."""
        return [CancelReason(**reason) for reason in CANCEL_REASONS]
    
    async def cancel_booking(
        self,
        reservation_no: str,
        cancellation_id: int
    ) -> TransferCancelResponse:
        """Cancel a booking."""
        
        if reservation_no not in _mock_bookings:
            raise ValueError("Reservation not found")
        
        booking = _mock_bookings[reservation_no]
        
        if not booking["is_cancelable"]:
            raise ValueError("This booking cannot be cancelled")
        
        # Update status
        booking["status"] = TransferStatus.CANCELLED.value
        booking["is_cancelable"] = False
        
        # Calculate refund (full refund for mock)
        refund = booking["price"]["total"]
        
        return TransferCancelResponse(
            status="Success",
            message="Refund successful.",
            refund_amount=refund
        )
    
    def _find_airport(self, pickup: Location, dropoff: Location) -> dict:
        """Find airport info from locations."""
        # Check pickup first
        for airport in AIRPORTS:
            if pickup.type == LocationType.AIRPORT:
                if (str(pickup.location_id) == str(airport["id"]) or
                    str(pickup.location_id).upper() == airport["code"]):
                    return airport
        
        # Check dropoff
        for airport in AIRPORTS:
            if dropoff.type == LocationType.AIRPORT:
                if (str(dropoff.location_id) == str(airport["id"]) or
                    str(dropoff.location_id).upper() == airport["code"]):
                    return airport
        
        # Default to first airport
        return AIRPORTS[0]
    
    def _generate_vehicles(self, distance: float, passengers: int) -> List[Vehicle]:
        """Generate vehicle options with pricing."""
        vehicles = []
        
        for idx, template in enumerate(VEHICLE_TEMPLATES):
            # Skip if not enough capacity
            if template["max_passengers"] < passengers:
                continue
            
            # Select random make/model
            make, model = random.choice(template["makes"])
            
            # Calculate price based on distance
            price = round(template["base_price"] + (distance * random.uniform(1.5, 2.5)), 2)
            
            # Random company
            company_data = random.choice(COMPANIES)
            
            vehicle = Vehicle(
                id=1000 + idx,
                make=make,
                model=model,
                segment=template["segment"],
                type=template["type"],
                price=price,
                currency="USD",
                min_passengers=1,
                max_passengers=template["max_passengers"],
                suitcase=template["suitcase"],
                small_bag=template["small_bag"],
                image=template["image"],
                company=VehicleCompany(**company_data)
            )
            vehicles.append(vehicle)
        
        # Sort by price
        vehicles.sort(key=lambda v: v.price)
        
        return vehicles


# Singleton instance
mock_transfer_client = MockTransferClient()
