"""
Search Service - Orchestrates search across suppliers with filtering and policy tagging.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import Organization
from app.models.employee import Employee
from app.schemas.search import (
    FlightSearchRequest, FlightSearchResponse, FlightOffer, FlightSegment,
    HotelSearchRequest, HotelSearchResponse, HotelOffer,
    PolicyStatus, SortBy
)
from app.services.suppliers.mock_flight_client import mock_flight_client, AIRPORTS
from app.services.suppliers.mock_hotel_client import mock_hotel_client, CITIES


class SearchService:
    """
    Handles search operations with filtering and policy-aware tagging.
    """
    
    @staticmethod
    async def search_flights(
        db: AsyncSession,
        request: FlightSearchRequest,
        current_user: Employee
    ) -> FlightSearchResponse:
        """
        Search for flights with filters and tag results with policy compliance.
        """
        # 1. Get org policy settings
        stmt = select(Organization).where(Organization.id == current_user.org_id)
        result = await db.execute(stmt)
        org = result.scalars().first()
        
        policy_settings = org.policy_settings if org else {}
        
        # 2. Call supplier with filters
        departure_dt = datetime.combine(request.departure_date, datetime.min.time())
        raw_offers = mock_flight_client.search_flights(
            origin=request.origin.upper(),
            destination=request.destination.upper(),
            departure_date=departure_dt,
            return_date=datetime.combine(request.return_date, datetime.min.time()) if request.return_date else None,
            passengers=request.passengers,
            cabin_class=request.cabin_class.value,
            # Filters
            max_price=request.max_price,
            max_stops=request.max_stops,
            airlines=request.airlines,
            refundable_only=request.refundable_only,
            max_duration_hours=request.max_duration_hours,
        )
        
        # 3. Normalize and tag with policy
        offers = []
        for raw in raw_offers:
            # Parse segments
            segments = [
                FlightSegment(
                    departure_airport=seg["departure_airport"],
                    departure_city=seg["departure_city"],
                    arrival_airport=seg["arrival_airport"],
                    arrival_city=seg["arrival_city"],
                    departure_time=datetime.fromisoformat(seg["departure_time"]),
                    arrival_time=datetime.fromisoformat(seg["arrival_time"]),
                    carrier_code=seg["carrier_code"],
                    carrier_name=seg["carrier_name"],
                    flight_number=seg["flight_number"],
                    duration_minutes=seg["duration_minutes"],
                )
                for seg in raw["segments"]
            ]
            
            # Apply policy tagging
            policy_status, policy_notes = SearchService._tag_flight_policy(
                raw, policy_settings, current_user
            )
            
            offer = FlightOffer(
                id=raw["id"],
                supplier=raw["supplier"],
                price=raw["price"],
                currency=raw["currency"],
                duration_minutes=raw["duration_minutes"],
                stops=raw["stops"],
                cabin_class=raw["cabin_class"],
                refundable=raw["refundable"],
                segments=segments,
                policy_status=policy_status,
                policy_notes=policy_notes,
                created_at=datetime.fromisoformat(raw["created_at"]),
            )
            offers.append(offer)
        
        # 4. Apply sorting
        offers = SearchService._sort_flight_offers(offers, request.sort_by)
        
        # 5. Calculate price range
        prices = [o.price for o in offers] if offers else [0]
        
        # Build filters applied dict
        filters_applied = {}
        if request.max_price:
            filters_applied["max_price"] = request.max_price
        if request.max_stops is not None:
            filters_applied["max_stops"] = request.max_stops
        if request.airlines:
            filters_applied["airlines"] = request.airlines
        if request.refundable_only:
            filters_applied["refundable_only"] = True
        if request.max_duration_hours:
            filters_applied["max_duration_hours"] = request.max_duration_hours
        
        # Get city names
        origin_city = AIRPORTS.get(request.origin.upper(), {}).get("city", request.origin)
        dest_city = AIRPORTS.get(request.destination.upper(), {}).get("city", request.destination)
        
        return FlightSearchResponse(
            origin=request.origin.upper(),
            origin_city=origin_city,
            destination=request.destination.upper(),
            destination_city=dest_city,
            departure_date=request.departure_date,
            offers=offers,
            total_results=len(offers),
            search_id=f"search_{uuid.uuid4().hex[:8]}",
            filters_applied=filters_applied,
            price_range={"min": min(prices), "max": max(prices)},
        )
    
    @staticmethod
    async def search_hotels(
        db: AsyncSession,
        request: HotelSearchRequest,
        current_user: Employee
    ) -> HotelSearchResponse:
        """
        Search for hotels with filters and tag results with policy compliance.
        """
        # 1. Get org policy settings
        stmt = select(Organization).where(Organization.id == current_user.org_id)
        result = await db.execute(stmt)
        org = result.scalars().first()
        
        policy_settings = org.policy_settings if org else {}
        
        # 2. Call supplier with filters
        checkin_dt = datetime.combine(request.checkin_date, datetime.min.time())
        checkout_dt = datetime.combine(request.checkout_date, datetime.min.time()) if request.checkout_date else None
        
        raw_offers = mock_hotel_client.search_hotels(
            city=request.city,
            checkin_date=checkin_dt,
            checkout_date=checkout_dt,
            guests=request.guests,
            rooms=request.rooms,
            # Filters
            max_price_per_night=request.max_price_per_night,
            min_stars=request.min_stars,
            max_stars=request.max_stars,
            chains=request.chains,
            amenities=request.amenities,
            free_cancellation=request.free_cancellation,
            breakfast_included=request.breakfast_included,
        )
        
        # 3. Normalize and tag with policy
        offers = []
        for raw in raw_offers:
            # Apply policy tagging
            policy_status, policy_notes = SearchService._tag_hotel_policy(
                raw, policy_settings
            )
            
            offer = HotelOffer(
                id=raw["id"],
                supplier=raw["supplier"],
                chain_code=raw["chain_code"],
                chain_name=raw["chain_name"],
                hotel_name=raw["hotel_name"],
                stars=raw["stars"],
                hotel_type=raw["hotel_type"],
                city=raw["city"],
                country=raw["country"],
                location=raw["location"],
                price_per_night=raw["price_per_night"],
                total_price=raw["total_price"],
                currency=raw["currency"],
                nights=raw["nights"],
                rooms=raw["rooms"],
                room_type=raw["room_type"],
                amenities=raw["amenities"],
                cancellation_policy=raw["cancellation_policy"],
                checkin_date=raw["checkin_date"],
                checkout_date=raw["checkout_date"],
                rating=raw["rating"],
                review_count=raw["review_count"],
                distance_to_center=raw["distance_to_center"],
                policy_status=policy_status,
                policy_notes=policy_notes,
                created_at=datetime.fromisoformat(raw["created_at"]),
            )
            offers.append(offer)
        
        # 4. Apply sorting
        offers = SearchService._sort_hotel_offers(offers, request.sort_by)
        
        # 5. Calculate price range
        prices = [o.price_per_night for o in offers] if offers else [0]
        
        # Filters applied
        filters_applied = {}
        if request.max_price_per_night:
            filters_applied["max_price_per_night"] = request.max_price_per_night
        if request.min_stars:
            filters_applied["min_stars"] = request.min_stars
        if request.max_stars:
            filters_applied["max_stars"] = request.max_stars
        if request.chains:
            filters_applied["chains"] = request.chains
        if request.amenities:
            filters_applied["amenities"] = request.amenities
        if request.free_cancellation:
            filters_applied["free_cancellation"] = True
        if request.breakfast_included:
            filters_applied["breakfast_included"] = True
        
        # Get country
        city_info = CITIES.get(request.city.lower(), {"country": "US"})
        
        return HotelSearchResponse(
            city=request.city.title(),
            country=city_info["country"],
            checkin_date=request.checkin_date,
            checkout_date=request.checkout_date,
            offers=offers,
            total_results=len(offers),
            search_id=f"search_{uuid.uuid4().hex[:8]}",
            filters_applied=filters_applied,
            price_range={"min": min(prices), "max": max(prices)},
        )
    
    @staticmethod
    def _sort_flight_offers(offers: List[FlightOffer], sort_by: SortBy) -> List[FlightOffer]:
        """Sort flight offers."""
        if sort_by == SortBy.PRICE:
            return sorted(offers, key=lambda x: x.price)
        elif sort_by == SortBy.DURATION:
            return sorted(offers, key=lambda x: x.duration_minutes)
        elif sort_by == SortBy.DEPARTURE:
            return sorted(offers, key=lambda x: x.segments[0].departure_time if x.segments else datetime.max)
        elif sort_by == SortBy.ARRIVAL:
            return sorted(offers, key=lambda x: x.segments[-1].arrival_time if x.segments else datetime.max)
        return offers
    
    @staticmethod
    def _sort_hotel_offers(offers: List[HotelOffer], sort_by: SortBy) -> List[HotelOffer]:
        """Sort hotel offers."""
        if sort_by == SortBy.PRICE:
            return sorted(offers, key=lambda x: x.price_per_night)
        elif sort_by == SortBy.RATING:
            return sorted(offers, key=lambda x: -x.rating)  # Descending
        return offers
    
    @staticmethod
    def _tag_flight_policy(
        offer: dict, 
        policy_settings: dict, 
        user: Employee
    ) -> tuple[PolicyStatus, List[str]]:
        """Tag a flight offer with policy compliance status."""
        notes = []
        status = PolicyStatus.COMPLIANT
        
        price = offer.get("price", 0)
        cabin_class = offer.get("cabin_class", "economy")
        
        # 1. Cost check
        max_amount = policy_settings.get("max_amount", 1000.0)
        if price > max_amount * 1.5:
            status = PolicyStatus.VIOLATION
            notes.append(f"Price ${price:.0f} exceeds limit ${max_amount:.0f} by more than 50%")
        elif price > max_amount:
            if status != PolicyStatus.VIOLATION:
                status = PolicyStatus.WARNING
            notes.append(f"Price ${price:.0f} exceeds limit ${max_amount:.0f}")
        
        # 2. Cabin class check
        if cabin_class in ["business", "first"]:
            allowed_titles = policy_settings.get("business_class_titles", ["CEO", "CTO", "CFO", "Director"])
            user_title = user.job_title or ""
            
            is_eligible = any(allowed in user_title for allowed in allowed_titles)
            if not is_eligible:
                if status != PolicyStatus.VIOLATION:
                    status = PolicyStatus.WARNING
                notes.append(f"{cabin_class.title()} class requires manager approval")
        
        return status, notes
    
    @staticmethod
    def _tag_hotel_policy(
        offer: dict, 
        policy_settings: dict
    ) -> tuple[PolicyStatus, List[str]]:
        """Tag a hotel offer with policy compliance status."""
        notes = []
        status = PolicyStatus.COMPLIANT
        
        price_per_night = offer.get("price_per_night", 0)
        
        # Cost check (per night)
        max_hotel_rate = policy_settings.get("max_hotel_rate", 200.0)
        
        if price_per_night > max_hotel_rate * 1.5:
            status = PolicyStatus.VIOLATION
            notes.append(f"Rate ${price_per_night:.0f}/night exceeds limit ${max_hotel_rate:.0f} by more than 50%")
        elif price_per_night > max_hotel_rate:
            status = PolicyStatus.WARNING
            notes.append(f"Rate ${price_per_night:.0f}/night exceeds limit ${max_hotel_rate:.0f}")
        
        # Luxury hotel check
        if offer.get("stars", 0) >= 5:
            max_stars = policy_settings.get("max_hotel_stars", 4)
            if offer["stars"] > max_stars:
                if status != PolicyStatus.VIOLATION:
                    status = PolicyStatus.WARNING
                notes.append(f"{offer['stars']}-star hotel requires approval")
        
        return status, notes
