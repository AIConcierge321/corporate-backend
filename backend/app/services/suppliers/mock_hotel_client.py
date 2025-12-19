"""
Mock Hotel Search Client - Enhanced with more cities and filtering.
"""

from datetime import datetime, timezone
from typing import List, Optional
import random
import uuid


# Hotel chains
HOTEL_CHAINS = [
    {"code": "HIL", "name": "Hilton"},
    {"code": "MAR", "name": "Marriott"},
    {"code": "HYT", "name": "Hyatt"},
    {"code": "IHG", "name": "InterContinental"},
    {"code": "WYN", "name": "Wyndham"},
    {"code": "BW", "name": "Best Western"},
    {"code": "CHO", "name": "Choice Hotels"},
    {"code": "ACC", "name": "Accor"},
    {"code": "RAD", "name": "Radisson"},
    {"code": "SHA", "name": "Shangri-La"},
]

# Hotel types with price multipliers
HOTEL_TYPES = [
    {"type": "budget", "stars": 2, "price_mult": 0.4},
    {"type": "economy", "stars": 3, "price_mult": 0.7},
    {"type": "standard", "stars": 3, "price_mult": 0.9},
    {"type": "upscale", "stars": 4, "price_mult": 1.3},
    {"type": "luxury", "stars": 5, "price_mult": 2.2},
]

AMENITIES = [
    "Free WiFi", "Free Breakfast", "Pool", "Gym", "Spa",
    "Restaurant", "Business Center", "Room Service", "Parking",
    "Airport Shuttle", "Pet Friendly", "Concierge", "Laundry",
    "Bar/Lounge", "Meeting Rooms", "EV Charging",
]

# Major cities with base hotel prices
CITIES = {
    # US
    "new york": {"country": "US", "base_price": 250},
    "los angeles": {"country": "US", "base_price": 180},
    "chicago": {"country": "US", "base_price": 160},
    "san francisco": {"country": "US", "base_price": 220},
    "miami": {"country": "US", "base_price": 190},
    "seattle": {"country": "US", "base_price": 170},
    "denver": {"country": "US", "base_price": 140},
    "boston": {"country": "US", "base_price": 200},
    "atlanta": {"country": "US", "base_price": 130},
    "dallas": {"country": "US", "base_price": 140},
    "las vegas": {"country": "US", "base_price": 120},
    "orlando": {"country": "US", "base_price": 130},
    "phoenix": {"country": "US", "base_price": 110},
    "houston": {"country": "US", "base_price": 130},
    
    # International
    "london": {"country": "UK", "base_price": 280},
    "paris": {"country": "FR", "base_price": 260},
    "frankfurt": {"country": "DE", "base_price": 200},
    "amsterdam": {"country": "NL", "base_price": 220},
    "dubai": {"country": "AE", "base_price": 200},
    "singapore": {"country": "SG", "base_price": 220},
    "hong kong": {"country": "HK", "base_price": 230},
    "tokyo": {"country": "JP", "base_price": 200},
    "seoul": {"country": "KR", "base_price": 150},
    "sydney": {"country": "AU", "base_price": 200},
    "toronto": {"country": "CA", "base_price": 180},
    "mumbai": {"country": "IN", "base_price": 100},
    "bangalore": {"country": "IN", "base_price": 90},
    "delhi": {"country": "IN", "base_price": 95},
}


def search_cities(query: str) -> List[dict]:
    """Search cities for hotel search autocomplete."""
    query = query.lower().strip()
    results = []
    
    for city, info in CITIES.items():
        if query in city:
            results.append({
                "city": city.title(),
                "country": info["country"],
            })
    
    return results[:15]


class MockHotelClient:
    """
    Generates realistic mock hotel search results with filtering.
    """
    
    def search_hotels(
        self,
        city: str,
        checkin_date: datetime,
        checkout_date: Optional[datetime] = None,
        guests: int = 1,
        rooms: int = 1,
        # Filters
        max_price_per_night: Optional[float] = None,
        min_stars: Optional[int] = None,
        max_stars: Optional[int] = None,
        chains: Optional[List[str]] = None,
        amenities: Optional[List[str]] = None,
        free_cancellation: bool = False,
        breakfast_included: bool = False,
    ) -> List[dict]:
        """
        Generate mock hotel offers with filtering.
        """
        city_lower = city.lower().strip()
        city_info = CITIES.get(city_lower, {"country": "US", "base_price": 150})
        
        offers = []
        num_offers = random.randint(10, 20)
        
        # Calculate nights
        if checkout_date:
            nights = (checkout_date - checkin_date).days
        else:
            nights = 1
        nights = max(1, nights)
        
        for i in range(num_offers):
            chain = random.choice(HOTEL_CHAINS)
            hotel_type = random.choice(HOTEL_TYPES)
            
            # Apply chain filter
            if chains and chain["code"] not in chains:
                continue
            
            # Apply star filter
            if min_stars and hotel_type["stars"] < min_stars:
                continue
            if max_stars and hotel_type["stars"] > max_stars:
                continue
            
            # Calculate price
            base_price = city_info["base_price"]
            price_per_night = int(base_price * hotel_type["price_mult"] * random.uniform(0.8, 1.3))
            total_price = price_per_night * nights * rooms
            
            # Apply price filter
            if max_price_per_night and price_per_night > max_price_per_night:
                continue
            
            # Random amenities
            num_amenities = random.randint(4, 10)
            hotel_amenities = random.sample(AMENITIES, num_amenities)
            
            # Apply amenity filter
            if amenities:
                if not all(a in hotel_amenities for a in amenities):
                    continue
            
            # Breakfast filter
            has_breakfast = "Free Breakfast" in hotel_amenities
            if breakfast_included and not has_breakfast:
                continue
            
            # Room types
            room_types = ["Standard Room", "Deluxe Room", "Suite", "King Room", "Double Room", "Executive Room"]
            room_type = random.choice(room_types)
            
            # Cancellation policy
            cancellation = random.choice([
                "free_cancellation",
                "non_refundable",
                "partial_refund",
            ])
            
            # Apply cancellation filter
            if free_cancellation and cancellation != "free_cancellation":
                continue
            
            # Location within city
            locations = ["Downtown", "Airport", "Central", "Plaza", "Business District", "Waterfront"]
            location = random.choice(locations)
            
            offer = {
                "id": f"hotel_{uuid.uuid4().hex[:12]}",
                "supplier": "mock",
                "chain_code": chain["code"],
                "chain_name": chain["name"],
                "hotel_name": f"{chain['name']} {city.title()} {location}",
                "stars": hotel_type["stars"],
                "hotel_type": hotel_type["type"],
                "city": city.title(),
                "country": city_info["country"],
                "location": location,
                "price_per_night": float(price_per_night),
                "total_price": float(total_price),
                "currency": "USD",
                "nights": nights,
                "rooms": rooms,
                "room_type": room_type,
                "amenities": hotel_amenities,
                "cancellation_policy": cancellation,
                "checkin_date": checkin_date.isoformat(),
                "checkout_date": (checkin_date.replace(day=checkin_date.day + nights)).isoformat() if checkout_date is None else checkout_date.isoformat(),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "review_count": random.randint(50, 3000),
                "distance_to_center": round(random.uniform(0.1, 10.0), 1),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            offers.append(offer)
        
        # Sort by total price
        offers.sort(key=lambda x: x["total_price"])
        
        return offers


# Singleton instance
mock_hotel_client = MockHotelClient()
