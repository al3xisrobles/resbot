"""
City configuration constants for multi-city support
"""

CITIES = {
    "nyc": {
        "id": "nyc",
        "name": "New York City",
        "center": {"lat": 40.7589, "lng": -73.9851},  # Times Square
        "bounds": {
            "sw": {"lat": 40.7, "lng": -74.02},
            "ne": {"lat": 40.8, "lng": -73.93},
        },
        "radius": 16100,  # ~10 miles in meters
    },
    "chicago": {
        "id": "chicago",
        "name": "Chicago",
        "center": {"lat": 41.8781, "lng": -87.6298},
        "bounds": {
            "sw": {"lat": 41.7, "lng": -87.9},
            "ne": {"lat": 42.0, "lng": -87.5},
        },
        "radius": 16100,  # ~10 miles in meters
    },
    "losAngeles": {
        "id": "losAngeles",
        "name": "Los Angeles",
        "center": {"lat": 34.0522, "lng": -118.2437},
        "bounds": {
            "sw": {"lat": 33.7, "lng": -118.7},
            "ne": {"lat": 34.3, "lng": -118.0},
        },
        "radius": 16100,  # ~10 miles in meters
    },
    "sanFrancisco": {
        "id": "sanFrancisco",
        "name": "San Francisco",
        "center": {"lat": 37.7749, "lng": -122.4194},
        "bounds": {
            "sw": {"lat": 37.7, "lng": -122.6},
            "ne": {"lat": 37.8, "lng": -122.3},
        },
        "radius": 16100,  # ~10 miles in meters
    },
    "boston": {
        "id": "boston",
        "name": "Boston",
        "center": {"lat": 42.3601, "lng": -71.0589},
        "bounds": {
            "sw": {"lat": 42.2, "lng": -71.2},
            "ne": {"lat": 42.4, "lng": -70.9},
        },
        "radius": 16100,  # ~10 miles in meters
    },
}

DEFAULT_CITY_ID = "nyc"


def get_city_config(city_id: str):
    """Get city configuration by ID, defaulting to NYC if not found."""
    return CITIES.get(city_id, CITIES[DEFAULT_CITY_ID])
