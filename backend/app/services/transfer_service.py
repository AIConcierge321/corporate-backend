"""
Transfer Service - Provides the transfer client based on configuration.

Switches between mock and real AirportTransfer API.
"""

from datetime import datetime

# Type hints for the interface
from typing import Protocol

from app.core.config import settings
from app.schemas.transfer import (
    AirportSearchResult,
    CancelReason,
    Location,
    PassengerInfo,
    TransferBookingDetails,
    TransferBookingResponse,
    TransferCancelResponse,
    TransferQuoteResponse,
    Travelers,
)
from app.services.suppliers.mock_transfer_client import MockTransferClient


class TransferClientProtocol(Protocol):
    """Protocol defining the transfer client interface."""

    async def search_airports(self, query: str) -> list[AirportSearchResult]: ...

    async def get_quotes(
        self,
        pickup_location: Location,
        drop_of_location: Location,
        flight_arrival: datetime,
        travelers: Travelers,
    ) -> TransferQuoteResponse: ...

    async def create_booking(
        self,
        search_id: str,
        vehicle_id: str,
        passenger: PassengerInfo,
        suitcase: int,
        small_bags: int,
        travel_details: dict | None,
    ) -> TransferBookingResponse: ...

    async def get_booking(self, reservation_no: str) -> TransferBookingDetails: ...

    async def get_cancel_reasons(self) -> list[CancelReason]: ...

    async def cancel_booking(
        self, reservation_no: str, cancellation_id: int
    ) -> TransferCancelResponse: ...


def get_transfer_client() -> TransferClientProtocol:
    """
    Get the appropriate transfer client based on configuration.

    - If AIRPORT_TRANSFER_USE_MOCK=True or no API key: Use mock client
    - Otherwise: Use real AirportTransfer API client
    """
    if settings.AIRPORT_TRANSFER_USE_MOCK or not settings.AIRPORT_TRANSFER_API_KEY:
        return MockTransferClient()

    # Import real client only when needed (to avoid import error if httpx missing)
    from app.services.suppliers.airport_transfer_client import AirportTransferClient

    return AirportTransferClient()
