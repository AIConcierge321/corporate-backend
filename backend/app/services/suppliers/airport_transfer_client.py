"""
AirportTransfer.com Partner API Client

Real API client for ground transport/taxi transfers.
API Docs: https://docs.airporttransfer.com/api

Tech Support:
- emine@airporttransfer.com
- hasan@airporttransfer.com
"""

import httpx
from datetime import datetime
from typing import List, Optional
import logging

from app.core.config import settings
from app.schemas.transfer import (
    AirportSearchResult, TransferQuoteResponse, QuoteAirport, Vehicle, VehicleCompany,
    TransferBookingResponse, TransferBookingDetails, DriverInfo, BookingPrice,
    CancelReason, TransferCancelResponse, Location, Travelers, PassengerInfo,
    LocationType, TransferStatus
)

logger = logging.getLogger(__name__)


class AirportTransferAPIError(Exception):
    """Error from AirportTransfer API."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"AirportTransfer API Error ({status_code}): {message}")


class AirportTransferClient:
    """
    Client for AirportTransfer.com Partner API.
    
    API Base: https://api.airporttransfer.com
    Auth: API Key in header (X-Api-Key or similar)
    """
    
    def __init__(self):
        self.base_url = settings.AIRPORT_TRANSFER_BASE_URL.rstrip("/")
        self.api_key = settings.AIRPORT_TRANSFER_API_KEY
        
        if not self.api_key:
            raise ValueError(
                "AIRPORT_TRANSFER_API_KEY not configured. "
                "Contact emine@airporttransfer.com or hasan@airporttransfer.com to get one."
            )
    
    def _get_headers(self) -> dict:
        """Get headers with API key."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,  # Or "Authorization": f"Bearer {self.api_key}"
        }
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make HTTP request to AirportTransfer API."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        async with httpx.AsyncClient(timeout=15.0) as client:  # MED-004: Reduced timeout
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                
                if response.status_code == 422:
                    raise AirportTransferAPIError(422, "Access Key Error - check your API key")
                
                if response.status_code == 404:
                    raise AirportTransferAPIError(404, "Resource not found")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"AirportTransfer API error: {e}")
                raise AirportTransferAPIError(e.response.status_code, str(e))
            except httpx.RequestError as e:
                logger.error(f"AirportTransfer API connection error: {e}")
                raise AirportTransferAPIError(500, f"Connection error: {e}")
    
    async def search_airports(self, query: str) -> List[AirportSearchResult]:
        """
        Search airports by name, code, or city.
        
        GET /location-search?search={query}
        """
        data = await self._request("GET", "/location-search", params={"search": query})
        
        return [
            AirportSearchResult(
                id=item["id"],
                name=item["name"],
                code=item["code"],
                description=item["description"]
            )
            for item in data
        ]
    
    async def get_quotes(
        self,
        pickup_location: Location,
        drop_of_location: Location,
        flight_arrival: datetime,
        travelers: Travelers
    ) -> TransferQuoteResponse:
        """
        Get transfer quotes for a route.
        
        POST /quotes
        """
        payload = {
            "booking_type": "ONEWAY",
            "pickup_location": self._format_location(pickup_location),
            "drop_of_location": self._format_location(drop_of_location),
            "flight_arrival": flight_arrival.strftime("%Y-%m-%d %H:%M"),
            "travelers": {
                "adult": travelers.adult,
                "children": travelers.children,
                "infant": travelers.infant
            }
        }
        
        data = await self._request("POST", "/quotes", json=payload)
        
        # Parse vehicles
        vehicles = []
        for v in data.get("vehicles", []):
            company = None
            if v.get("company"):
                company = VehicleCompany(
                    name=v["company"].get("name", ""),
                    rating=v["company"].get("rating"),
                    review_count=v["company"].get("review_count")
                )
            
            vehicles.append(Vehicle(
                id=v["id"],
                make=v.get("make", ""),
                model=v.get("model", ""),
                segment=v.get("segment", ""),
                type=v.get("type", ""),
                price=v["price"],
                currency=v.get("currency", "USD"),
                min_passengers=v.get("min_passengers", 1),
                max_passengers=v.get("max_passengers", 4),
                suitcase=v.get("suitcase", 2),
                small_bag=v.get("small_bag", 2),
                image=v.get("image", ""),
                company=company
            ))
        
        airport = data.get("airport", {})
        
        return TransferQuoteResponse(
            search_id=data["searchID"],
            airport=QuoteAirport(
                id=airport.get("id", 0),
                name=airport.get("name", ""),
                code=airport.get("code", "")
            ),
            vehicles=vehicles,
            distance=data.get("distance", 0),
            dealer_count=data.get("dealer_count", 0),
            search_status=data.get("search_status", "OK")
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
        """
        Create a transfer booking.
        
        POST /new-booking
        """
        payload = {
            "searchID": search_id,
            "vehicle_id": vehicle_id,
            "passenger": {
                "gender": passenger.gender,
                "name": passenger.name,
                "surname": passenger.surname,
                "email": passenger.email,
                "phone": passenger.phone,
                "flight_number": passenger.flight_number
            },
            "suitcase": suitcase,
            "small_bags": small_bags
        }
        
        if travel_details:
            payload["travel_details"] = travel_details
        
        data = await self._request("POST", "/new-booking", json=payload)
        
        return TransferBookingResponse(
            status=data["status"],
            message=data["message"],
            reservation_no=data["data"]["reservation_no"],
            search_id=data["data"].get("search_id", search_id)
        )
    
    async def get_booking(self, reservation_no: str) -> TransferBookingDetails:
        """
        Get booking details.
        
        GET /booking?reservation_no={reservation_no}
        
        Poll every 10 minutes until status is APPROVED to get driver info.
        """
        data = await self._request("GET", "/booking", params={"reservation_no": reservation_no})
        
        booking = data["booking"]
        vehicle_data = data.get("vehicle", booking.get("vehicle", {}))
        
        # Parse driver (only available when APPROVED)
        driver = None
        if booking.get("driver"):
            driver_data = booking["driver"]
            if isinstance(driver_data, list) and driver_data:
                driver_data = driver_data[0]
            if driver_data:
                driver = DriverInfo(
                    name=driver_data.get("name"),
                    phone=driver_data.get("phone"),
                    vehicle_plate=driver_data.get("vehicle_plate")
                )
        
        return TransferBookingDetails(
            reservation_no=booking["reservation_no"],
            status=TransferStatus(booking["status"]),
            pickup_location=Location(
                location_id=booking["pickup_location"].get("id", ""),
                type=LocationType(booking["pickup_location"].get("type", "PLACE"))
            ),
            drop_of_location=Location(
                location_id=booking["drop_of_location"].get("id", ""),
                type=LocationType(booking["drop_of_location"].get("type", "PLACE"))
            ),
            passenger=PassengerInfo(
                gender=booking["passenger"].get("gender", "Mr"),
                name=booking["passenger"].get("name", ""),
                surname=booking["passenger"].get("surname", ""),
                email=booking["passenger"].get("email", ""),
                phone=booking["passenger"].get("phone", ""),
                flight_number=booking["passenger"].get("flight_number")
            ),
            driver=driver,
            travelers=Travelers(
                adult=booking["travelers"].get("adult", 1),
                children=booking["travelers"].get("children", 0),
                infant=booking["travelers"].get("infant", 0)
            ),
            price=BookingPrice(
                total=booking["price"]["total"],
                currency=booking["price"].get("currency", "USD")
            ),
            vehicle=Vehicle(
                id=vehicle_data.get("id", 0),
                make=vehicle_data.get("make", ""),
                model=vehicle_data.get("model", ""),
                segment=vehicle_data.get("segment", ""),
                type=vehicle_data.get("type", ""),
                price=vehicle_data.get("price", 0),
                currency=vehicle_data.get("currency", "USD"),
                min_passengers=vehicle_data.get("min_passengers", 1),
                max_passengers=vehicle_data.get("max_passengers", 4),
                suitcase=vehicle_data.get("suitcase", 2),
                small_bag=vehicle_data.get("small_bag", 2),
                image=vehicle_data.get("image", "")
            ),
            distance=booking.get("distance", 0),
            booking_type=booking.get("booking_type", "ONEWAY"),
            is_cancelable=booking.get("is_cancelable", True),
            created_at=datetime.fromisoformat(booking["created_at"].replace("Z", "+00:00"))
        )
    
    async def get_cancel_reasons(self) -> List[CancelReason]:
        """
        Get available cancellation reasons.
        
        GET /cancel-reasons
        """
        data = await self._request("GET", "/cancel-reasons")
        
        return [
            CancelReason(
                id=item["id"],
                cancellation_name=item["cancellation_name"],
                cancellation_description=item.get("cancellation_description")
            )
            for item in data
        ]
    
    async def cancel_booking(
        self,
        reservation_no: str,
        cancellation_id: int
    ) -> TransferCancelResponse:
        """
        Cancel a booking.
        
        POST /cancel-booking
        """
        payload = {
            "reservation_no": reservation_no,
            "cancellation_id": cancellation_id
        }
        
        data = await self._request("POST", "/cancel-booking", json=payload)
        
        return TransferCancelResponse(
            status=data["status"],
            message=data["message"],
            refund_amount=data.get("data", {}).get("refund_amount")
        )
    
    def _format_location(self, location: Location) -> dict:
        """Format location for API request."""
        if location.lat and location.lng:
            # Coordinate-based location
            return {
                "name": location.name or "Location",
                "lat": str(location.lat),
                "lng": str(location.lng),
                "type": location.type.value
            }
        else:
            # ID-based location (airport ID, IATA code, or place ID)
            return {
                "location_id": location.location_id,
                "type": location.type.value
            }


# Singleton instance (created lazily when API key is available)
_airport_transfer_client: Optional[AirportTransferClient] = None


def get_airport_transfer_client() -> AirportTransferClient:
    """Get or create the AirportTransfer API client."""
    global _airport_transfer_client
    if _airport_transfer_client is None:
        _airport_transfer_client = AirportTransferClient()
    return _airport_transfer_client
