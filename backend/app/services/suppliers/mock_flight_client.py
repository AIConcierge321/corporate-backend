"""
Mock Flight Search Client - Enhanced with more destinations and business hubs.
"""

import operator
import random
import uuid
from datetime import UTC, datetime, timedelta

# Airlines with codes
AIRLINES = [
    {"code": "UA", "name": "United Airlines"},
    {"code": "AA", "name": "American Airlines"},
    {"code": "DL", "name": "Delta Air Lines"},
    {"code": "SW", "name": "Southwest Airlines"},
    {"code": "JB", "name": "JetBlue Airways"},
    {"code": "AS", "name": "Alaska Airlines"},
    {"code": "B6", "name": "Spirit Airlines"},
    {"code": "NK", "name": "Frontier Airlines"},
]

# Comprehensive airport/city database
AIRPORTS = {
    # US Major Hubs
    "JFK": {
        "city": "New York",
        "name": "John F. Kennedy International",
        "country": "US",
        "hub": True,
    },
    "LGA": {"city": "New York", "name": "LaGuardia", "country": "US", "hub": False},
    "EWR": {"city": "Newark", "name": "Newark Liberty International", "country": "US", "hub": True},
    "LAX": {
        "city": "Los Angeles",
        "name": "Los Angeles International",
        "country": "US",
        "hub": True,
    },
    "ORD": {"city": "Chicago", "name": "O'Hare International", "country": "US", "hub": True},
    "SFO": {
        "city": "San Francisco",
        "name": "San Francisco International",
        "country": "US",
        "hub": True,
    },
    "MIA": {"city": "Miami", "name": "Miami International", "country": "US", "hub": True},
    "SEA": {
        "city": "Seattle",
        "name": "Seattle-Tacoma International",
        "country": "US",
        "hub": True,
    },
    "DEN": {"city": "Denver", "name": "Denver International", "country": "US", "hub": True},
    "BOS": {"city": "Boston", "name": "Logan International", "country": "US", "hub": True},
    "ATL": {
        "city": "Atlanta",
        "name": "Hartsfield-Jackson International",
        "country": "US",
        "hub": True,
    },
    "DFW": {
        "city": "Dallas",
        "name": "Dallas/Fort Worth International",
        "country": "US",
        "hub": True,
    },
    "PHX": {"city": "Phoenix", "name": "Phoenix Sky Harbor", "country": "US", "hub": False},
    "IAH": {
        "city": "Houston",
        "name": "George Bush Intercontinental",
        "country": "US",
        "hub": True,
    },
    "LAS": {"city": "Las Vegas", "name": "Harry Reid International", "country": "US", "hub": False},
    "MCO": {"city": "Orlando", "name": "Orlando International", "country": "US", "hub": False},
    "CLT": {
        "city": "Charlotte",
        "name": "Charlotte Douglas International",
        "country": "US",
        "hub": True,
    },
    "MSP": {
        "city": "Minneapolis",
        "name": "Minneapolis-St. Paul International",
        "country": "US",
        "hub": True,
    },
    "DTW": {"city": "Detroit", "name": "Detroit Metropolitan", "country": "US", "hub": True},
    "PHL": {
        "city": "Philadelphia",
        "name": "Philadelphia International",
        "country": "US",
        "hub": True,
    },
    # International Business Hubs
    "LHR": {"city": "London", "name": "Heathrow", "country": "UK", "hub": True},
    "CDG": {"city": "Paris", "name": "Charles de Gaulle", "country": "FR", "hub": True},
    "FRA": {"city": "Frankfurt", "name": "Frankfurt Airport", "country": "DE", "hub": True},
    "AMS": {"city": "Amsterdam", "name": "Schiphol", "country": "NL", "hub": True},
    "DXB": {"city": "Dubai", "name": "Dubai International", "country": "AE", "hub": True},
    "SIN": {"city": "Singapore", "name": "Changi Airport", "country": "SG", "hub": True},
    "HKG": {"city": "Hong Kong", "name": "Hong Kong International", "country": "HK", "hub": True},
    "NRT": {"city": "Tokyo", "name": "Narita International", "country": "JP", "hub": True},
    "ICN": {"city": "Seoul", "name": "Incheon International", "country": "KR", "hub": True},
    "SYD": {"city": "Sydney", "name": "Sydney Airport", "country": "AU", "hub": True},
    "YYZ": {"city": "Toronto", "name": "Pearson International", "country": "CA", "hub": True},
    "MEX": {
        "city": "Mexico City",
        "name": "Benito Juárez International",
        "country": "MX",
        "hub": True,
    },
    "GRU": {"city": "São Paulo", "name": "Guarulhos International", "country": "BR", "hub": True},
    "BOM": {"city": "Mumbai", "name": "Chhatrapati Shivaji", "country": "IN", "hub": True},
    "DEL": {"city": "Delhi", "name": "Indira Gandhi International", "country": "IN", "hub": True},
    "BLR": {"city": "Bangalore", "name": "Kempegowda International", "country": "IN", "hub": True},
}

# City to airport mapping for city search
CITY_TO_AIRPORTS = {}
for code, info in AIRPORTS.items():
    city = info["city"].lower()
    if city not in CITY_TO_AIRPORTS:
        CITY_TO_AIRPORTS[city] = []
    CITY_TO_AIRPORTS[city].append(code)


def search_airports(query: str, business_hubs_only: bool = False) -> list[dict]:
    """
    Search airports by city name, airport code, or airport name.
    """
    query = query.lower().strip()
    results = []

    for code, info in AIRPORTS.items():
        # Skip non-hubs if filtering
        if business_hubs_only and not info.get("hub", False):
            continue

        # Match by code, city, or name
        if query in code.lower() or query in info["city"].lower() or query in info["name"].lower():
            results.append({
                "code": code,
                "city": info["city"],
                "name": info["name"],
                "country": info["country"],
                "is_hub": info.get("hub", False),
            })

    # Sort by hub status first, then by exact code match
    results.sort(key=lambda x: (not x["is_hub"], x["code"] != query.upper()))
    return results[:20]  # Limit results


class MockFlightClient:
    """
    Generates realistic mock flight search results with filtering.
    """

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        return_date: datetime | None = None,
        passengers: int = 1,
        cabin_class: str = "economy",
        # Filters
        max_price: float | None = None,
        max_stops: int | None = None,
        airlines: list[str] | None = None,
        refundable_only: bool = False,
        max_duration_hours: int | None = None,
    ) -> list[dict]:
        """
        Generate mock flight offers with filtering support.
        """
        if origin not in AIRPORTS or destination not in AIRPORTS:
            return []

        offers = []
        num_offers = random.randint(8, 20)

        for _i in range(num_offers):
            airline = random.choice(AIRLINES)

            # Skip if airline filter doesn't match
            if airlines and airline["code"] not in airlines:
                continue

            # Generate realistic flight times
            dep_hour = random.randint(5, 23)
            dep_minute = random.choice([0, 15, 30, 45])
            departure_time = departure_date.replace(
                hour=dep_hour, minute=dep_minute, second=0, microsecond=0, tzinfo=UTC
            )

            # Flight duration based on distance (simplified)
            is_international = AIRPORTS[origin]["country"] != AIRPORTS[destination]["country"]
            if is_international:
                duration_minutes = random.randint(360, 900)  # 6-15 hours
            else:
                duration_minutes = random.randint(90, 360)  # 1.5-6 hours

            # Apply duration filter
            if max_duration_hours and duration_minutes > max_duration_hours * 60:
                continue

            arrival_time = departure_time + timedelta(minutes=duration_minutes)

            # Pricing based on cabin class
            base_prices = {
                "economy": random.randint(150, 800),
                "premium_economy": random.randint(400, 1200),
                "business": random.randint(1500, 5000),
                "first": random.randint(4000, 15000),
            }

            # International flights cost more
            price = base_prices.get(cabin_class, base_prices["economy"])
            if is_international:
                price = int(price * random.uniform(1.5, 2.5))

            price = int(price * passengers * random.uniform(0.85, 1.25))

            # Apply price filter
            if max_price and price > max_price:
                continue

            # Generate stops
            stops = random.choices([0, 1, 2], weights=[50, 35, 15])[0]

            # Apply stops filter
            if max_stops is not None and stops > max_stops:
                continue

            # Refundability
            refundable = random.choice([True, False, False, False])  # 25% chance

            # Apply refundable filter
            if refundable_only and not refundable:
                continue

            offer = {
                "id": f"offer_{uuid.uuid4().hex[:12]}",
                "supplier": "mock",
                "price": float(price),
                "currency": "USD",
                "duration_minutes": duration_minutes,
                "stops": stops,
                "cabin_class": cabin_class,
                "refundable": refundable,
                "segments": [
                    {
                        "departure_airport": origin,
                        "departure_city": AIRPORTS[origin]["city"],
                        "arrival_airport": destination,
                        "arrival_city": AIRPORTS[destination]["city"],
                        "departure_time": departure_time.isoformat(),
                        "arrival_time": arrival_time.isoformat(),
                        "carrier_code": airline["code"],
                        "carrier_name": airline["name"],
                        "flight_number": f"{airline['code']}{random.randint(100, 9999)}",
                        "duration_minutes": duration_minutes,
                    }
                ],
                "created_at": datetime.now(UTC).isoformat(),
            }

            offers.append(offer)

        # Sort by price
        offers.sort(key=operator.itemgetter("price"))

        return offers


# Singleton instance
mock_flight_client = MockFlightClient()
