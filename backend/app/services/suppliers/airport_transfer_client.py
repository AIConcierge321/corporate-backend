"""
AirportTransfer.com Partner API Client

Production-ready client for ground transport/taxi transfers.
API Docs: https://docs.airporttransfer.com/api

Features:
- Retry with exponential backoff
- Circuit breaker pattern
- Request/response logging
- Sandbox/Production environment switching

Tech Support:
- emine@airporttransfer.com
- hasan@airporttransfer.com
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

import httpx

from app.core.config import settings
from app.schemas.transfer import (
    AirportSearchResult,
    BookingPrice,
    CancelReason,
    DriverInfo,
    Location,
    LocationType,
    PassengerInfo,
    QuoteAirport,
    TransferBookingDetails,
    TransferBookingResponse,
    TransferCancelResponse,
    TransferQuoteResponse,
    TransferStatus,
    Travelers,
    Vehicle,
    VehicleCompany,
)

logger = logging.getLogger(__name__)


# ==================== Exceptions ====================


class AirportTransferAPIError(Exception):
    """Base error from AirportTransfer API."""

    def __init__(self, status_code: int, message: str, details: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"AirportTransfer API Error ({status_code}): {message}")


class AirportTransferRateLimitError(AirportTransferAPIError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limit exceeded. Retry after {retry_after}s")


class AirportTransferUnavailableError(AirportTransferAPIError):
    """Service temporarily unavailable (circuit breaker open)."""

    def __init__(self):
        super().__init__(503, "Service temporarily unavailable. Circuit breaker is open.")


# ==================== Circuit Breaker ====================


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures.

    States:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and datetime.now() > self.last_failure_time + timedelta(
                seconds=self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logger.info("Circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
                return True
            return False

        if self.state == "HALF_OPEN":
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False

    def record_success(self):
        """Record a successful request."""
        if self.state == "HALF_OPEN":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED (service recovered)")
        elif self.state == "CLOSED":
            self.failure_count = 0

    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning("Circuit breaker: HALF_OPEN -> OPEN (failure during recovery)")
        elif self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker: CLOSED -> OPEN (threshold {self.failure_threshold} reached)"
            )


# ==================== Main Client ====================


class AirportTransferClient:
    """
    Production-ready client for AirportTransfer.com Partner API.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker for fault tolerance
    - Configurable sandbox/production environments
    - Request/response logging

    Environment Variables:
    - AIRPORT_TRANSFER_API_KEY: Your API key
    - AIRPORT_TRANSFER_USE_SANDBOX: True for sandbox, False for production
    """

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 1.0  # seconds
    RETRY_BACKOFF_MAX = 10.0  # seconds

    # Timeout configuration
    CONNECT_TIMEOUT = 5.0  # seconds
    READ_TIMEOUT = 15.0  # seconds

    # Retryable status codes
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(self):
        # Determine environment
        self.is_sandbox = settings.AIRPORT_TRANSFER_USE_SANDBOX

        if self.is_sandbox:
            self.base_url = settings.AIRPORT_TRANSFER_SANDBOX_URL.rstrip("/")
            self.environment = "SANDBOX"
        else:
            self.base_url = settings.AIRPORT_TRANSFER_BASE_URL.rstrip("/")
            self.environment = "PRODUCTION"

        self.api_key = settings.AIRPORT_TRANSFER_API_KEY

        if not self.api_key:
            raise ValueError(
                "AIRPORT_TRANSFER_API_KEY not configured. "
                "Contact emine@airporttransfer.com or hasan@airporttransfer.com for access."
            )

        # Circuit breaker (shared across all requests)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60, half_open_max_calls=3
        )

        logger.info(f"AirportTransfer client initialized: {self.environment} mode")

    def _get_headers(self) -> dict:
        """Get headers with API key authentication."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
            "User-Agent": "AI-Concierge-Corporate-Travel/1.0",
        }

    async def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Make HTTP request with retry logic and circuit breaker.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx

        Returns:
            API response as dict

        Raises:
            AirportTransferAPIError: On API errors
            AirportTransferUnavailableError: When circuit breaker is open
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise AirportTransferUnavailableError()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(self.MAX_RETRIES):
            try:
                # Log request (debug level)
                if attempt > 0:
                    logger.debug(f"Retry {attempt}/{self.MAX_RETRIES} for {method} {endpoint}")

                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=self.CONNECT_TIMEOUT,
                        read=self.READ_TIMEOUT,
                        write=self.READ_TIMEOUT,
                        pool=self.READ_TIMEOUT,
                    )
                ) as client:
                    start_time = time.time()

                    response = await client.request(
                        method=method, url=url, headers=headers, **kwargs
                    )

                    duration = time.time() - start_time

                    # Log response (debug level)
                    logger.debug(f"{method} {endpoint} -> {response.status_code} ({duration:.2f}s)")

                    # Handle specific status codes
                    if response.status_code == 422:
                        self.circuit_breaker.record_success()  # Not a service failure
                        raise AirportTransferAPIError(
                            422, "Invalid API key or request", {"response": response.text[:200]}
                        )

                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        raise AirportTransferRateLimitError(retry_after)

                    if response.status_code in self.RETRYABLE_STATUS_CODES:
                        raise httpx.HTTPStatusError(
                            f"Retryable error: {response.status_code}",
                            request=response.request,
                            response=response,
                        )

                    response.raise_for_status()

                    # Success!
                    self.circuit_breaker.record_success()
                    return response.json()

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else 500

                if status_code in self.RETRYABLE_STATUS_CODES and attempt < self.MAX_RETRIES - 1:
                    # Calculate backoff with jitter
                    backoff = min(self.RETRY_BACKOFF_BASE * (2**attempt), self.RETRY_BACKOFF_MAX)
                    logger.warning(f"Request failed ({status_code}), retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    continue

                # Non-retryable or exhausted retries
                self.circuit_breaker.record_failure()
                logger.error(f"AirportTransfer API error: {e}")
                raise AirportTransferAPIError(
                    status_code, str(e), {"response": e.response.text[:200] if e.response else None}
                )

            except httpx.RequestError as e:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = min(self.RETRY_BACKOFF_BASE * (2**attempt), self.RETRY_BACKOFF_MAX)
                    logger.warning(f"Connection error, retrying in {backoff:.1f}s: {e}")
                    await asyncio.sleep(backoff)
                    continue

                # Exhausted retries
                self.circuit_breaker.record_failure()
                logger.error(f"AirportTransfer connection error: {e}")
                raise AirportTransferAPIError(500, f"Connection error: {e}")

        # Should not reach here, but just in case
        self.circuit_breaker.record_failure()
        raise AirportTransferAPIError(500, f"Request failed after {self.MAX_RETRIES} retries")

    # ==================== API Methods ====================

    async def search_airports(self, query: str) -> list[AirportSearchResult]:
        """
        Search airports by name, code, or city.

        GET /location-search?search={query}

        Args:
            query: Search term (min 2 characters)

        Returns:
            List of matching airports
        """
        if len(query) < 2:
            return []

        data = await self._request_with_retry("GET", "/location-search", params={"search": query})

        return [
            AirportSearchResult(
                id=item["id"],
                name=item["name"],
                code=item["code"],
                description=item.get("description", ""),
            )
            for item in data
        ]

    async def get_quotes(
        self,
        pickup_location: Location,
        drop_of_location: Location,
        flight_arrival: datetime,
        travelers: Travelers,
    ) -> TransferQuoteResponse:
        """
        Get transfer quotes for a route.

        POST /quotes

        Note: One location must be an AIRPORT.
        For PLACE locations, use GPS coordinates (lat/lng).

        Args:
            pickup_location: Pickup point (airport or place with coordinates)
            drop_of_location: Drop-off point (airport or place with coordinates)
            flight_arrival: Flight arrival datetime
            travelers: Number of travelers by type

        Returns:
            Available vehicles with pricing
        """
        payload = {
            "booking_type": "ONEWAY",
            "pickup_location": self._format_location(pickup_location),
            "drop_of_location": self._format_location(drop_of_location),
            "flight_arrival": flight_arrival.strftime("%Y-%m-%d %H:%M"),
            "travelers": {
                "adult": travelers.adult,
                "children": travelers.children,
                "infant": travelers.infant,
            },
        }

        data = await self._request_with_retry("POST", "/quotes", json=payload)

        # Parse vehicles
        vehicles = []
        for v in data.get("vehicles", []):
            company = None
            if v.get("company"):
                company = VehicleCompany(
                    name=v["company"].get("name", ""),
                    rating=v["company"].get("rating"),
                    review_count=v["company"].get("review_count"),
                )

            vehicles.append(
                Vehicle(
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
                    company=company,
                )
            )

        airport = data.get("airport", {})

        return TransferQuoteResponse(
            search_id=data["searchID"],
            airport=QuoteAirport(
                id=airport.get("id", 0), name=airport.get("name", ""), code=airport.get("code", "")
            ),
            vehicles=vehicles,
            distance=data.get("distance", 0),
            dealer_count=data.get("dealer_count", 0),
            search_status=data.get("search_status", "OK"),
        )

    async def create_booking(
        self,
        search_id: str,
        vehicle_id: str,
        passenger: PassengerInfo,
        suitcase: int = 0,
        small_bags: int = 0,
        travel_details: dict | None = None,
    ) -> TransferBookingResponse:
        """
        Create a transfer booking.

        POST /new-booking

        Args:
            search_id: Search ID from get_quotes()
            vehicle_id: Selected vehicle ID
            passenger: Lead passenger information
            suitcase: Number of large suitcases
            small_bags: Number of small bags
            travel_details: Optional flight/airline details

        Returns:
            Booking confirmation with reservation number
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
                "flight_number": passenger.flight_number,
            },
            "suitcase": suitcase,
            "small_bags": small_bags,
        }

        if travel_details:
            payload["travel_details"] = travel_details

        data = await self._request_with_retry("POST", "/new-booking", json=payload)

        return TransferBookingResponse(
            status=data["status"],
            message=data["message"],
            reservation_no=data["data"]["reservation_no"],
            search_id=data["data"].get("search_id", search_id),
        )

    async def get_booking(self, reservation_no: str) -> TransferBookingDetails:
        """
        Get booking details.

        GET /booking?reservation_no={reservation_no}

        Note: Driver info is only available when status is APPROVED.
        Poll every 10 minutes until status changes from PENDING.

        Args:
            reservation_no: Reservation number (e.g., AT-123456789-ABC)

        Returns:
            Full booking details including driver info (if approved)
        """
        data = await self._request_with_retry(
            "GET", "/booking", params={"reservation_no": reservation_no}
        )

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
                    vehicle_plate=driver_data.get("vehicle_plate"),
                )

        return TransferBookingDetails(
            reservation_no=booking["reservation_no"],
            status=TransferStatus(booking["status"]),
            pickup_location=Location(
                location_id=booking["pickup_location"].get("id", ""),
                type=LocationType(booking["pickup_location"].get("type", "PLACE")),
            ),
            drop_of_location=Location(
                location_id=booking["drop_of_location"].get("id", ""),
                type=LocationType(booking["drop_of_location"].get("type", "PLACE")),
            ),
            passenger=PassengerInfo(
                gender=booking["passenger"].get("gender", "Mr"),
                name=booking["passenger"].get("name", ""),
                surname=booking["passenger"].get("surname", ""),
                email=booking["passenger"].get("email", ""),
                phone=booking["passenger"].get("phone", ""),
                flight_number=booking["passenger"].get("flight_number"),
            ),
            driver=driver,
            travelers=Travelers(
                adult=booking["travelers"].get("adult", 1),
                children=booking["travelers"].get("children", 0),
                infant=booking["travelers"].get("infant", 0),
            ),
            price=BookingPrice(
                total=booking["price"]["total"], currency=booking["price"].get("currency", "USD")
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
                image=vehicle_data.get("image", ""),
            ),
            distance=booking.get("distance", 0),
            booking_type=booking.get("booking_type", "ONEWAY"),
            is_cancelable=booking.get("is_cancelable", True),
            created_at=datetime.fromisoformat(booking["created_at"]),
        )

    async def get_cancel_reasons(self) -> list[CancelReason]:
        """
        Get available cancellation reasons.

        GET /cancel-reasons

        Returns:
            List of cancellation reasons with IDs
        """
        data = await self._request_with_retry("GET", "/cancel-reasons")

        return [
            CancelReason(
                id=item["id"],
                cancellation_name=item["cancellation_name"],
                cancellation_description=item.get("cancellation_description"),
            )
            for item in data
        ]

    async def cancel_booking(
        self, reservation_no: str, cancellation_id: int
    ) -> TransferCancelResponse:
        """
        Cancel a booking.

        POST /cancel-booking

        Note: Free cancellation up to 48 hours before service time.

        Args:
            reservation_no: Reservation number to cancel
            cancellation_id: Reason ID from get_cancel_reasons()

        Returns:
            Cancellation confirmation with refund amount
        """
        payload = {"reservation_no": reservation_no, "cancellation_id": cancellation_id}

        data = await self._request_with_retry("POST", "/cancel-booking", json=payload)

        return TransferCancelResponse(
            status=data["status"],
            message=data["message"],
            refund_amount=data.get("data", {}).get("refund_amount"),
        )

    def _format_location(self, location: Location) -> dict:
        """Format location for API request."""
        if location.lat and location.lng:
            # Coordinate-based location (for PLACE)
            return {
                "name": location.name or "Location",
                "lat": str(location.lat),
                "lng": str(location.lng),
                "type": location.type.value,
            }
        # ID-based location (for AIRPORT - IATA code)
        return {"location_id": location.location_id, "type": location.type.value}

    def get_status(self) -> dict:
        """Get client status information."""
        return {
            "provider": "AirportTransfer.com",
            "environment": self.environment,
            "base_url": self.base_url,
            "circuit_breaker_state": self.circuit_breaker.state,
            "api_key_configured": bool(self.api_key),
        }


# ==================== Singleton Factory ====================

_airport_transfer_client: AirportTransferClient | None = None


def get_airport_transfer_client() -> AirportTransferClient:
    """Get or create the AirportTransfer API client (singleton)."""
    global _airport_transfer_client
    if _airport_transfer_client is None:
        _airport_transfer_client = AirportTransferClient()
    return _airport_transfer_client


def reset_airport_transfer_client():
    """Reset the client (useful for testing or config changes)."""
    global _airport_transfer_client
    _airport_transfer_client = None
