"""
All Aboard Train API Client

GraphQL client for European rail booking.
API Docs: https://docs.allaboard.eu/

Uses:
- HTTP POST for queries/mutations
- WebSocket (graphql-ws) for subscriptions (journey search, offers)
"""

import httpx
import websockets
import json
import uuid
import asyncio
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.schemas.train import (
    Station, StationSearchResponse,
    Journey, JourneyLeg, StationTime, TrainSearchResponse,
    Offer, OfferResponse, Price,
    Booking, BookingStatus,
    Order, OrderStatus, Ticket,
    PassengerInput, PassengerDetails,
    PassengerType, ServiceClass, Flexibility
)

logger = logging.getLogger(__name__)


class AllAboardAPIError(Exception):
    """Error from All Aboard API."""
    def __init__(self, message: str, errors: Optional[List[Dict]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(message)


class AllAboardClient:
    """
    GraphQL client for All Aboard train booking API.
    
    Uses HTTP POST for GraphQL queries/mutations.
    Uses WebSocket (graphql-ws protocol) for streaming subscriptions.
    """
    
    def __init__(self):
        self.api_key = settings.ALLABOARD_API_KEY
        
        # Use test or production environment
        if settings.ALLABOARD_USE_TEST:
            self.base_url = "https://test.api-gateway.allaboard.eu"
            self.ws_url = "wss://test.api-gateway.allaboard.eu"
        else:
            self.base_url = settings.ALLABOARD_BASE_URL
            self.ws_url = settings.ALLABOARD_BASE_URL.replace("https://", "wss://")
    
    def _get_headers(self) -> dict:
        """Get headers with authorization."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            # All Aboard uses 'api-key' header, not Bearer token
            headers["api-key"] = self.api_key
        return headers
    
    async def _execute_graphql(
        self,
        query: str,
        variables: Optional[Dict] = None,
        operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query/mutation via HTTP POST."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                    raise AllAboardAPIError(error_msg, data["errors"])
                
                return data.get("data", {})
                
            except httpx.HTTPStatusError as e:
                logger.error(f"All Aboard API HTTP error: {e}")
                raise AllAboardAPIError(f"HTTP error: {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"All Aboard API connection error: {e}")
                raise AllAboardAPIError(f"Connection error: {e}")
    
    async def _execute_subscription(
        self,
        query: str,
        variables: Optional[Dict] = None,
        timeout_seconds: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Execute a GraphQL subscription via WebSocket (graphql-ws protocol).
        
        Collects all streamed results until the subscription completes.
        """
        results = []
        subscription_id = str(uuid.uuid4())
        
        try:
            # Connect with subprotocol
            async with websockets.connect(
                self.ws_url,
                subprotocols=["graphql-transport-ws"],
                additional_headers={"api-key": self.api_key} if self.api_key else None
            ) as ws:
                # 1. Send connection_init
                await ws.send(json.dumps({
                    "type": "connection_init",
                    "payload": {"api-key": self.api_key} if self.api_key else {}
                }))
                
                # 2. Wait for connection_ack
                ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if ack.get("type") != "connection_ack":
                    raise AllAboardAPIError(f"Connection not acknowledged: {ack}")
                
                # 3. Send subscribe
                await ws.send(json.dumps({
                    "id": subscription_id,
                    "type": "subscribe",
                    "payload": {
                        "query": query,
                        "variables": variables or {}
                    }
                }))
                
                # 4. Collect results until complete
                start_time = asyncio.get_event_loop().time()
                while True:
                    remaining = timeout_seconds - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        break
                    
                    try:
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5)))
                    except asyncio.TimeoutError:
                        continue
                    
                    msg_type = msg.get("type")
                    
                    if msg_type == "next":
                        # Got a result
                        payload = msg.get("payload", {})
                        if "data" in payload:
                            results.append(payload["data"])
                    elif msg_type == "error":
                        errors = msg.get("payload", [])
                        raise AllAboardAPIError(
                            errors[0].get("message") if errors else "Subscription error",
                            errors
                        )
                    elif msg_type == "complete":
                        # Subscription finished
                        break
                
                # 5. Send complete to clean up
                await ws.send(json.dumps({
                    "id": subscription_id,
                    "type": "complete"
                }))
                
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            raise AllAboardAPIError(f"WebSocket error: {e}")
        
        return results
    
    # ==================== Station Search ====================
    
    async def search_stations(self, query: str) -> StationSearchResponse:
        """
        Search for train stations by name or city.
        
        GraphQL: query { getLocations(query: "...") }
        """
        gql = """
        query GetLocations($query: String!) {
            getLocations(query: $query) {
                uid
                name
            }
        }
        """
        
        data = await self._execute_graphql(gql, {"query": query})
        locations = data.get("getLocations", [])
        
        stations = [
            Station(
                uid=loc["uid"],
                name=loc["name"]
            )
            for loc in locations
        ]
        
        return StationSearchResponse(stations=stations, total=len(stations))
    
    # ==================== Journey Search ====================
    
    async def search_journeys(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: List[PassengerInput]
    ) -> TrainSearchResponse:
        """
        Search for train journeys.
        
        Uses GraphQL SUBSCRIPTION via WebSocket for streaming results.
        The API streams Journey objects with itinerary containing SegmentCollections.
        """
        gql = """
        subscription GetJourneys(
            $origin: ID!,
            $destination: ID!,
            $date: Date!,
            $passengers: [PassengerPlaceholderInput!]!
        ) {
            getJourneys(
                origin: $origin,
                destination: $destination,
                date: $date,
                passengers: $passengers
            ) {
                id
                status
                itinerary {
                    ... on SegmentCollection {
                        status
                        segments {
                            origin {
                                name
                            }
                            destination {
                                name
                            }
                            departureAt
                            arrivalAt
                            duration
                            transport
                            operator {
                                name
                            }
                            identifier
                        }
                    }
                }
            }
        }
        """
        
        # Format passengers for API
        passenger_inputs = [
            {"type": p.type.value, "age": p.age}
            for p in passengers
        ]
        
        variables = {
            "origin": origin,
            "destination": destination,
            "date": departure_date.isoformat(),
            "passengers": passenger_inputs
        }
        
        # Use WebSocket subscription for streaming
        results = await self._execute_subscription(gql, variables, timeout_seconds=30)
        
        # Merge all streamed results
        journeys = []
        origin_station = None
        dest_station = None
        
        for data in results:
            journeys_data = data.get("getJourneys", [])
            if isinstance(journeys_data, dict):
                journeys_data = [journeys_data]
            
            for j in journeys_data:
                # Skip if still loading or error
                if j.get("status") != "SUCCESS":
                    continue
                    
                itinerary = j.get("itinerary", [])
                if not itinerary:
                    continue
                
                # Get first and last segments for departure/arrival times
                all_segments = []
                operators = set()
                
                for item in itinerary:
                    if not item:
                        continue
                    segments = item.get("segments", [])
                    all_segments.extend(segments)
                    for seg in segments:
                        if seg.get("operator", {}).get("name"):
                            operators.add(seg["operator"]["name"])
                
                if not all_segments:
                    continue
                
                first_seg = all_segments[0]
                last_seg = all_segments[-1]
                
                # Extract stations
                if not origin_station:
                    origin_station = Station(
                        uid=origin,
                        name=first_seg.get("origin", {}).get("name", "Origin")
                    )
                if not dest_station:
                    dest_station = Station(
                        uid=destination,
                        name=last_seg.get("destination", {}).get("name", "Destination")
                    )
                
                # Calculate total duration
                total_duration = sum(seg.get("duration", 0) for seg in all_segments)
                
                # Parse times
                dep_time = datetime.fromisoformat(first_seg["departureAt"].replace("Z", "+00:00"))
                arr_time = datetime.fromisoformat(last_seg["arrivalAt"].replace("Z", "+00:00"))
                
                journey = Journey(
                    uid=j["id"],
                    departure=dep_time,
                    arrival=arr_time,
                    duration_minutes=total_duration,
                    changes=len(all_segments) - 1,
                    operators=list(operators),
                    legs=None
                )
                journeys.append(journey)
        
        return TrainSearchResponse(
            journeys=journeys,
            origin=origin_station or Station(uid=origin, name="Origin"),
            destination=dest_station or Station(uid=destination, name="Destination"),
            search_date=departure_date,
            total_results=len(journeys)
        )
    
    # ==================== Offers ====================
    
    async def get_journey_offers(
        self,
        journey_uid: str,
        passengers: List[PassengerInput],
        currency: str = "EUR"
    ) -> OfferResponse:
        """
        Get offers/pricing for a specific journey.
        
        GraphQL: query { getJourneyOffer(...) }
        """
        # The getJourneyOffer returns a JourneyOffer type directly
        gql = """
        query GetJourneyOffer(
            $journey: ID!,
            $passengers: [PassengerPlaceholderInput!]!,
            $currency: String
        ) {
            getJourneyOffer(
                journey: $journey,
                passengers: $passengers,
                currency: $currency
            ) {
                uid
                price {
                    amount
                    currency
                }
                class
                flexibility
                operator {
                    name
                }
                conditions
            }
        }
        """
        
        passenger_inputs = [
            {"type": p.type.value, "age": p.age}
            for p in passengers
        ]
        
        variables = {
            "journey": journey_uid,
            "passengers": passenger_inputs,
            "currency": currency
        }
        
        data = await self._execute_graphql(gql, variables)
        offer_data = data.get("getJourneyOffer")
        
        # The API returns a single offer, not a list
        offers = []
        if offer_data:
            offers.append(
                Offer(
                    uid=offer_data["uid"],
                    price=Price(
                        amount=offer_data["price"]["amount"],
                        currency=offer_data["price"]["currency"]
                    ),
                    service_class=ServiceClass(offer_data.get("class", "STANDARD")),
                    flexibility=Flexibility(offer_data.get("flexibility", "NON_FLEX")),
                    operator=offer_data.get("operator", {}).get("name", ""),
                    conditions=offer_data.get("conditions")
                )
            )
        
        return OfferResponse(
            journey_uid=journey_uid,
            offers=offers,
            requirements=None
        )
    
    # ==================== Booking ====================
    
    async def create_booking(self, offer_uid: str) -> Booking:
        """
        Create a booking from an offer.
        
        GraphQL: mutation { createBooking(journeyOffer: "...") }
        """
        gql = """
        mutation CreateBooking($journeyOffer: ID!) {
            createBooking(journeyOffer: $journeyOffer) {
                uid
                status
                requirements
                createdAt
            }
        }
        """
        
        data = await self._execute_graphql(gql, {"journeyOffer": offer_uid})
        booking_data = data.get("createBooking", {})
        
        return Booking(
            uid=booking_data["uid"],
            status=BookingStatus(booking_data.get("status", "PENDING")),
            journey=None,  # Will be filled later
            offer=None,
            requirements=booking_data.get("requirements"),
            created_at=datetime.fromisoformat(booking_data["createdAt"].replace("Z", "+00:00"))
        )
    
    async def update_booking(
        self,
        booking_uid: str,
        passengers: List[PassengerDetails]
    ) -> Booking:
        """
        Update booking with passenger details.
        
        GraphQL: mutation { updateBooking(...) }
        """
        gql = """
        mutation UpdateBooking(
            $id: ID!,
            $passengers: [PassengerInput!]!
        ) {
            updateBooking(
                id: $id,
                passengers: $passengers
            ) {
                uid
                status
                requirements
            }
        }
        """
        
        # Format passenger details
        passenger_data = [
            {
                "type": p.type.value,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "email": p.email,
                "tel": p.phone,
                "birthDate": p.birth_date.isoformat() if p.birth_date else None,
                "isContactPerson": p.is_contact_person
            }
            for p in passengers
        ]
        
        data = await self._execute_graphql(gql, {
            "id": booking_uid,
            "passengers": passenger_data
        })
        booking_data = data.get("updateBooking", {})
        
        return Booking(
            uid=booking_data["uid"],
            status=BookingStatus(booking_data.get("status", "PENDING")),
            journey=None,
            offer=None,
            passengers=passengers,
            requirements=booking_data.get("requirements"),
            created_at=datetime.now()
        )
    
    # ==================== Order ====================
    
    async def create_order(self, booking_uid: str) -> Order:
        """
        Create an order (pre-book/hold tickets).
        
        GraphQL: mutation { createOrder(booking: "...") }
        """
        gql = """
        mutation CreateOrder($booking: ID!) {
            createOrder(booking: $booking) {
                uid
                status
                totalPrice {
                    amount
                    currency
                }
                createdAt
            }
        }
        """
        
        data = await self._execute_graphql(gql, {"booking": booking_uid})
        order_data = data.get("createOrder", {})
        
        return Order(
            uid=order_data["uid"],
            status=OrderStatus(order_data.get("status", "CREATED")),
            booking_uid=booking_uid,
            total_price=Price(
                amount=order_data["totalPrice"]["amount"],
                currency=order_data["totalPrice"]["currency"]
            ),
            created_at=datetime.fromisoformat(order_data["createdAt"].replace("Z", "+00:00"))
        )
    
    async def finalize_order(self, order_uid: str) -> Order:
        """
        Finalize order and issue tickets.
        
        GraphQL: mutation { finalizeOrder(order: "...") }
        """
        gql = """
        mutation FinalizeOrder($order: ID!) {
            finalizeOrder(order: $order) {
                uid
                status
                tickets {
                    uid
                    pdfUrl
                    checkinUrl
                    reference
                }
                totalPrice {
                    amount
                    currency
                }
                confirmedAt
            }
        }
        """
        
        data = await self._execute_graphql(gql, {"order": order_uid})
        order_data = data.get("finalizeOrder", {})
        
        tickets = [
            Ticket(
                uid=t["uid"],
                pdf_url=t.get("pdfUrl"),
                checkin_url=t.get("checkinUrl"),
                reference=t.get("reference")
            )
            for t in order_data.get("tickets", [])
        ]
        
        return Order(
            uid=order_data["uid"],
            status=OrderStatus(order_data.get("status", "FULFILLED")),
            booking_uid="",
            total_price=Price(
                amount=order_data["totalPrice"]["amount"],
                currency=order_data["totalPrice"]["currency"]
            ),
            tickets=tickets,
            created_at=datetime.now(),
            confirmed_at=datetime.fromisoformat(order_data["confirmedAt"].replace("Z", "+00:00")) if order_data.get("confirmedAt") else None
        )
    
    async def get_order(self, order_uid: str) -> Order:
        """
        Get order details.
        
        GraphQL: query { getOrder(id: "...") }
        """
        gql = """
        query GetOrder($id: ID!) {
            getOrder(id: $id) {
                uid
                status
                tickets {
                    uid
                    pdfUrl
                    checkinUrl
                    reference
                }
                totalPrice {
                    amount
                    currency
                }
                createdAt
                confirmedAt
            }
        }
        """
        
        data = await self._execute_graphql(gql, {"id": order_uid})
        order_data = data.get("getOrder", {})
        
        tickets = [
            Ticket(
                uid=t["uid"],
                pdf_url=t.get("pdfUrl"),
                checkin_url=t.get("checkinUrl"),
                reference=t.get("reference")
            )
            for t in order_data.get("tickets", [])
        ]
        
        return Order(
            uid=order_data["uid"],
            status=OrderStatus(order_data.get("status", "CREATED")),
            booking_uid="",
            total_price=Price(
                amount=order_data["totalPrice"]["amount"],
                currency=order_data["totalPrice"]["currency"]
            ),
            tickets=tickets,
            created_at=datetime.fromisoformat(order_data["createdAt"].replace("Z", "+00:00")),
            confirmed_at=datetime.fromisoformat(order_data["confirmedAt"].replace("Z", "+00:00")) if order_data.get("confirmedAt") else None
        )


# Singleton instance
def get_allaboard_client() -> AllAboardClient:
    """Get All Aboard client instance."""
    return AllAboardClient()
