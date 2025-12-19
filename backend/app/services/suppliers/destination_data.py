"""
Destination Intelligence Data

Business destinations with:
- Corporate rates and negotiated properties
- Travel insights (trips/year, clients, savings)
- Risk levels and visa requirements
- Preferred hotels and frequent routes
"""

from typing import List, Dict, Optional
from datetime import datetime
import random


# Risk levels
class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Presence types
class PresenceType:
    OFFICE = "office"
    ADVISORY = "advisory"
    CLIENT = "client"
    PARTNER = "partner"


# Regions
REGIONS = [
    "Europe",
    "Asia Pacific", 
    "North America",
    "Middle East",
    "Latin America",
    "Africa",
]


# Comprehensive destination database
DESTINATIONS = {
    "london": {
        "city": "London",
        "country": "United Kingdom",
        "country_code": "GB",
        "region": "Europe",
        "timezone": "Europe/London",
        "currency": "GBP",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        # Travel stats
        "trips_per_year": 145,
        "active_clients": 23,
        "market_savings_pct": 12,
        
        # Average costs
        "avg_flight_cost": 1850,
        "avg_hotel_rate": 245,
        "avg_flight_time_minutes": 440,  # 7h 20m
        
        # Preferred properties
        "preferred_hotels": 8,
        "preferred_hotels_list": [
            {"name": "The Savoy", "stars": 5, "rate": 450},
            {"name": "Hilton London Bankside", "stars": 4, "rate": 220},
            {"name": "Marriott County Hall", "stars": 4, "rate": 280},
            {"name": "InterContinental London", "stars": 5, "rate": 380},
            {"name": "Hyatt Regency London", "stars": 4, "rate": 245},
        ],
        
        # Business hub
        "is_hub": True,
        "hub_airports": ["LHR", "LGW", "STN"],
        
        # Quick facts
        "language": "English",
        "power_plug": "Type G",
        "emergency": "999",
    },
    
    "singapore": {
        "city": "Singapore",
        "country": "Singapore",
        "country_code": "SG",
        "region": "Asia Pacific",
        "timezone": "Asia/Singapore",
        "currency": "SGD",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 98,
        "active_clients": 15,
        "market_savings_pct": 8,
        
        "avg_flight_cost": 2100,
        "avg_hotel_rate": 280,
        "avg_flight_time_minutes": 1125,  # 18h 45m
        
        "preferred_hotels": 5,
        "preferred_hotels_list": [
            {"name": "Marina Bay Sands", "stars": 5, "rate": 450},
            {"name": "Shangri-La Singapore", "stars": 5, "rate": 380},
            {"name": "The Fullerton", "stars": 5, "rate": 420},
            {"name": "Hilton Singapore", "stars": 4, "rate": 250},
        ],
        
        "is_hub": True,
        "hub_airports": ["SIN"],
        "language": "English, Mandarin, Malay",
        "power_plug": "Type G",
        "emergency": "999",
    },
    
    "dubai": {
        "city": "Dubai",
        "country": "United Arab Emirates",
        "country_code": "AE",
        "region": "Middle East",
        "timezone": "Asia/Dubai",
        "currency": "AED",
        "presence": PresenceType.ADVISORY,
        "risk_level": RiskLevel.MEDIUM,
        "visa_required": True,
        
        "trips_per_year": 54,
        "active_clients": 8,
        "market_savings_pct": 15,
        
        "avg_flight_cost": 2450,
        "avg_hotel_rate": 320,
        "avg_flight_time_minutes": 870,  # 14h 30m
        
        "preferred_hotels": 6,
        "preferred_hotels_list": [
            {"name": "Burj Al Arab", "stars": 5, "rate": 1200},
            {"name": "Atlantis The Palm", "stars": 5, "rate": 450},
            {"name": "JW Marriott Marquis", "stars": 5, "rate": 280},
            {"name": "Hilton Dubai Creek", "stars": 4, "rate": 180},
        ],
        
        "is_hub": True,
        "hub_airports": ["DXB", "DWC"],
        "language": "Arabic, English",
        "power_plug": "Type G",
        "emergency": "999",
    },
    
    "tokyo": {
        "city": "Tokyo",
        "country": "Japan",
        "country_code": "JP",
        "region": "Asia Pacific",
        "timezone": "Asia/Tokyo",
        "currency": "JPY",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": True,
        
        "trips_per_year": 76,
        "active_clients": 12,
        "market_savings_pct": 10,
        
        "avg_flight_cost": 1980,
        "avg_hotel_rate": 265,
        "avg_flight_time_minutes": 795,  # 13h 15m
        
        "preferred_hotels": 7,
        "preferred_hotels_list": [
            {"name": "The Peninsula Tokyo", "stars": 5, "rate": 520},
            {"name": "Park Hyatt Tokyo", "stars": 5, "rate": 480},
            {"name": "Mandarin Oriental", "stars": 5, "rate": 450},
            {"name": "Hilton Tokyo", "stars": 4, "rate": 220},
            {"name": "Marriott Tokyo", "stars": 4, "rate": 240},
        ],
        
        "is_hub": True,
        "hub_airports": ["NRT", "HND"],
        "language": "Japanese",
        "power_plug": "Type A/B",
        "emergency": "110",
    },
    
    "paris": {
        "city": "Paris",
        "country": "France",
        "country_code": "FR",
        "region": "Europe",
        "timezone": "Europe/Paris",
        "currency": "EUR",
        "presence": PresenceType.CLIENT,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 87,
        "active_clients": 18,
        "market_savings_pct": 14,
        
        "avg_flight_cost": 1750,
        "avg_hotel_rate": 235,
        "avg_flight_time_minutes": 490,  # 8h 10m
        
        "preferred_hotels": 9,
        "preferred_hotels_list": [
            {"name": "Le Meurice", "stars": 5, "rate": 850},
            {"name": "Four Seasons George V", "stars": 5, "rate": 950},
            {"name": "Hyatt Regency Paris", "stars": 4, "rate": 280},
            {"name": "Hilton Paris Opera", "stars": 4, "rate": 245},
            {"name": "Marriott Champs-Elysées", "stars": 4, "rate": 320},
        ],
        
        "is_hub": True,
        "hub_airports": ["CDG", "ORY"],
        "language": "French",
        "power_plug": "Type C/E",
        "emergency": "112",
    },
    
    "toronto": {
        "city": "Toronto",
        "country": "Canada",
        "country_code": "CA",
        "region": "North America",
        "timezone": "America/Toronto",
        "currency": "CAD",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 62,
        "active_clients": 9,
        "market_savings_pct": 9,
        
        "avg_flight_cost": 450,
        "avg_hotel_rate": 195,
        "avg_flight_time_minutes": 165,  # 2h 45m
        
        "preferred_hotels": 6,
        "preferred_hotels_list": [
            {"name": "Fairmont Royal York", "stars": 5, "rate": 320},
            {"name": "Shangri-La Toronto", "stars": 5, "rate": 380},
            {"name": "Hilton Toronto", "stars": 4, "rate": 180},
            {"name": "Marriott Downtown", "stars": 4, "rate": 195},
        ],
        
        "is_hub": True,
        "hub_airports": ["YYZ"],
        "language": "English, French",
        "power_plug": "Type A/B",
        "emergency": "911",
    },
    
    "new york": {
        "city": "New York",
        "country": "United States",
        "country_code": "US",
        "region": "North America",
        "timezone": "America/New_York",
        "currency": "USD",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 234,
        "active_clients": 45,
        "market_savings_pct": 11,
        
        "avg_flight_cost": 380,
        "avg_hotel_rate": 285,
        "avg_flight_time_minutes": 0,  # HQ
        
        "preferred_hotels": 12,
        "preferred_hotels_list": [
            {"name": "The Plaza", "stars": 5, "rate": 650},
            {"name": "Four Seasons", "stars": 5, "rate": 780},
            {"name": "Marriott Marquis", "stars": 4, "rate": 320},
            {"name": "Hilton Midtown", "stars": 4, "rate": 280},
            {"name": "Hyatt Grand Central", "stars": 4, "rate": 265},
        ],
        
        "is_hub": True,
        "hub_airports": ["JFK", "LGA", "EWR"],
        "language": "English",
        "power_plug": "Type A/B",
        "emergency": "911",
    },
    
    "hong kong": {
        "city": "Hong Kong",
        "country": "Hong Kong SAR",
        "country_code": "HK",
        "region": "Asia Pacific",
        "timezone": "Asia/Hong_Kong",
        "currency": "HKD",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 68,
        "active_clients": 11,
        "market_savings_pct": 7,
        
        "avg_flight_cost": 2200,
        "avg_hotel_rate": 295,
        "avg_flight_time_minutes": 960,  # 16h
        
        "preferred_hotels": 6,
        "preferred_hotels_list": [
            {"name": "The Peninsula", "stars": 5, "rate": 580},
            {"name": "Mandarin Oriental", "stars": 5, "rate": 520},
            {"name": "Four Seasons", "stars": 5, "rate": 560},
            {"name": "Hyatt Regency", "stars": 4, "rate": 280},
        ],
        
        "is_hub": True,
        "hub_airports": ["HKG"],
        "language": "Cantonese, English",
        "power_plug": "Type G",
        "emergency": "999",
    },
    
    "frankfurt": {
        "city": "Frankfurt",
        "country": "Germany",
        "country_code": "DE",
        "region": "Europe",
        "timezone": "Europe/Berlin",
        "currency": "EUR",
        "presence": PresenceType.CLIENT,
        "risk_level": RiskLevel.LOW,
        "visa_required": False,
        
        "trips_per_year": 42,
        "active_clients": 7,
        "market_savings_pct": 13,
        
        "avg_flight_cost": 1650,
        "avg_hotel_rate": 215,
        "avg_flight_time_minutes": 510,  # 8h 30m
        
        "preferred_hotels": 5,
        "preferred_hotels_list": [
            {"name": "Jumeirah Frankfurt", "stars": 5, "rate": 380},
            {"name": "Hilton Frankfurt", "stars": 4, "rate": 195},
            {"name": "Marriott Frankfurt", "stars": 4, "rate": 210},
        ],
        
        "is_hub": True,
        "hub_airports": ["FRA"],
        "language": "German",
        "power_plug": "Type C/F",
        "emergency": "112",
    },
    
    "mumbai": {
        "city": "Mumbai",
        "country": "India",
        "country_code": "IN",
        "region": "Asia Pacific",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "presence": PresenceType.OFFICE,
        "risk_level": RiskLevel.LOW,
        "visa_required": True,
        
        "trips_per_year": 38,
        "active_clients": 6,
        "market_savings_pct": 18,
        
        "avg_flight_cost": 1450,
        "avg_hotel_rate": 165,
        "avg_flight_time_minutes": 1020,  # 17h
        
        "preferred_hotels": 5,
        "preferred_hotels_list": [
            {"name": "Taj Mahal Palace", "stars": 5, "rate": 320},
            {"name": "The Oberoi", "stars": 5, "rate": 280},
            {"name": "Four Seasons", "stars": 5, "rate": 350},
            {"name": "Hyatt Regency", "stars": 4, "rate": 150},
        ],
        
        "is_hub": True,
        "hub_airports": ["BOM"],
        "language": "Hindi, English",
        "power_plug": "Type C/D/M",
        "emergency": "112",
    },
    
    "sydney": {
        "city": "Sydney",
        "country": "Australia",
        "country_code": "AU",
        "region": "Asia Pacific",
        "timezone": "Australia/Sydney",
        "currency": "AUD",
        "presence": PresenceType.PARTNER,
        "risk_level": RiskLevel.LOW,
        "visa_required": True,
        
        "trips_per_year": 28,
        "active_clients": 4,
        "market_savings_pct": 10,
        
        "avg_flight_cost": 2800,
        "avg_hotel_rate": 245,
        "avg_flight_time_minutes": 1320,  # 22h
        
        "preferred_hotels": 4,
        "preferred_hotels_list": [
            {"name": "Park Hyatt Sydney", "stars": 5, "rate": 520},
            {"name": "Shangri-La Sydney", "stars": 5, "rate": 380},
            {"name": "Hilton Sydney", "stars": 4, "rate": 220},
        ],
        
        "is_hub": True,
        "hub_airports": ["SYD"],
        "language": "English",
        "power_plug": "Type I",
        "emergency": "000",
    },
    
    "sao paulo": {
        "city": "São Paulo",
        "country": "Brazil",
        "country_code": "BR",
        "region": "Latin America",
        "timezone": "America/Sao_Paulo",
        "currency": "BRL",
        "presence": PresenceType.CLIENT,
        "risk_level": RiskLevel.MEDIUM,
        "visa_required": True,
        
        "trips_per_year": 22,
        "active_clients": 5,
        "market_savings_pct": 16,
        
        "avg_flight_cost": 1850,
        "avg_hotel_rate": 185,
        "avg_flight_time_minutes": 600,  # 10h
        
        "preferred_hotels": 4,
        "preferred_hotels_list": [
            {"name": "Fasano São Paulo", "stars": 5, "rate": 380},
            {"name": "Tivoli Mofarrej", "stars": 5, "rate": 320},
            {"name": "Hilton Morumbi", "stars": 4, "rate": 165},
        ],
        
        "is_hub": True,
        "hub_airports": ["GRU"],
        "language": "Portuguese",
        "power_plug": "Type N",
        "emergency": "190",
    },
}

# Frequent routes (from HQ)
FREQUENT_ROUTES = [
    {
        "id": "route_1",
        "origin": "JFK",
        "origin_city": "New York",
        "destination": "LHR",
        "destination_city": "London",
        "trips_per_month": 12,
        "avg_price": 1850,
        "best_carrier": "British Airways",
        "avg_duration_minutes": 440,
    },
    {
        "id": "route_2",
        "origin": "JFK",
        "origin_city": "New York",
        "destination": "CDG",
        "destination_city": "Paris",
        "trips_per_month": 8,
        "avg_price": 1750,
        "best_carrier": "Air France",
        "avg_duration_minutes": 490,
    },
    {
        "id": "route_3",
        "origin": "JFK",
        "origin_city": "New York",
        "destination": "SIN",
        "destination_city": "Singapore",
        "trips_per_month": 6,
        "avg_price": 2100,
        "best_carrier": "Singapore Airlines",
        "avg_duration_minutes": 1125,
    },
    {
        "id": "route_4",
        "origin": "JFK",
        "origin_city": "New York",
        "destination": "YYZ",
        "destination_city": "Toronto",
        "trips_per_month": 15,
        "avg_price": 450,
        "best_carrier": "Air Canada",
        "avg_duration_minutes": 165,
    },
]


def search_destinations(
    query: Optional[str] = None,
    region: Optional[str] = None,
    hubs_only: bool = False,
) -> List[dict]:
    """Search destinations with optional filters."""
    results = []
    
    for key, dest in DESTINATIONS.items():
        # Apply region filter
        if region and dest["region"] != region:
            continue
            
        # Apply hub filter
        if hubs_only and not dest.get("is_hub", False):
            continue
            
        # Apply search query
        if query:
            query_lower = query.lower()
            if not (query_lower in dest["city"].lower() or
                    query_lower in dest["country"].lower() or
                    query_lower in key):
                continue
        
        results.append({
            "id": key,
            **dest
        })
    
    # Sort by trips per year (popularity)
    results.sort(key=lambda x: x.get("trips_per_year", 0), reverse=True)
    
    return results


def get_destination_stats() -> dict:
    """Get aggregate destination statistics."""
    total_destinations = len(DESTINATIONS)
    total_preferred_hotels = sum(d.get("preferred_hotels", 0) for d in DESTINATIONS.values())
    avg_savings = sum(d.get("market_savings_pct", 0) for d in DESTINATIONS.values()) / total_destinations
    total_routes = len(FREQUENT_ROUTES)
    
    return {
        "active_destinations": total_destinations,
        "preferred_hotels": total_preferred_hotels,
        "avg_savings_pct": round(avg_savings, 0),
        "frequent_routes": total_routes,
    }


def get_frequent_routes() -> List[dict]:
    """Get frequent travel routes."""
    return FREQUENT_ROUTES
