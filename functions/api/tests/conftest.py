"""
Shared pytest fixtures for search functionality tests.

This module provides reusable fixtures for:
- Mock venue data factories
- Availability status factories
- Search filter fixtures
- Mock Resy API responses
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import pytest
from unittest.mock import Mock, MagicMock


# =============================================================================
# Venue Factory
# =============================================================================

class VenueFactory:
    """Factory for creating mock venue data matching Resy API format."""

    _venue_counter = 0

    @classmethod
    def _next_id(cls) -> int:
        """Generate next venue ID."""
        cls._venue_counter += 1
        return cls._venue_counter

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the venue ID counter. Call this at the start of tests that depend on specific IDs."""
        cls._venue_counter = 0

    @staticmethod
    def create(
        venue_id: Optional[int] = None,
        name: Optional[str] = None,
        cuisine: Optional[str] = None,
        price_range_id: Optional[int] = None,
        locality: str = "New York",
        region: str = "NY",
        neighborhood: str = "Manhattan",
        latitude: float = 40.7589,
        longitude: float = -73.9851,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a single venue hit in Resy API format."""
        if venue_id is None:
            venue_id = VenueFactory._next_id()
        if name is None:
            name = f"Restaurant {venue_id}"
        if cuisine is None:
            cuisine = "American"
        if price_range_id is None:
            price_range_id = 2

        return {
            "_source": {
                "id": {"resy": venue_id},
                "name": name,
                "cuisine": [cuisine],
                "price_range_id": price_range_id,
                "locality": locality,
                "region": region,
                "neighborhood": neighborhood,
                "_geoloc": {
                    "lat": latitude,
                    "lng": longitude,
                },
                "images": [image_url] if image_url else [],
            }
        }

    @staticmethod
    def create_batch(
        count: int,
        cuisine: Optional[str] = None,
        price_range_id: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Create a batch of venues."""
        venues = []
        for i in range(count):
            venue_kwargs = kwargs.copy()
            if cuisine:
                venue_kwargs["cuisine"] = cuisine
            if price_range_id:
                venue_kwargs["price_range_id"] = price_range_id
            venues.append(VenueFactory.create(**venue_kwargs))
        return venues

    @staticmethod
    def with_cuisine(cuisine: str, count: int = 1) -> List[Dict[str, Any]]:
        """Create venues with specific cuisine."""
        return VenueFactory.create_batch(count, cuisine=cuisine)

    @staticmethod
    def with_price_range(price_range_id: int, count: int = 1) -> List[Dict[str, Any]]:
        """Create venues with specific price range."""
        return VenueFactory.create_batch(count, price_range_id=price_range_id)

    @staticmethod
    def mixed_cuisines(cuisines: List[str], count_per: int = 1) -> List[Dict[str, Any]]:
        """Create venues with mixed cuisines."""
        venues = []
        for cuisine in cuisines:
            venues.extend(VenueFactory.with_cuisine(cuisine, count_per))
        return venues

    @staticmethod
    def mixed_price_ranges(price_ranges: List[int], count_per: int = 1) -> List[Dict[str, Any]]:
        """Create venues with mixed price ranges."""
        venues = []
        for price_range in price_ranges:
            venues.extend(VenueFactory.with_price_range(price_range, count_per))
        return venues


# =============================================================================
# Availability Factory
# =============================================================================

class AvailabilityFactory:
    """Factory for creating availability status responses."""

    @staticmethod
    def available(times: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create availability response with available times."""
        if times is None:
            times = ["6:00 PM", "7:00 PM", "8:00 PM", "9:00 PM"]
        return {"times": times, "status": None}

    @staticmethod
    def not_released() -> Dict[str, Any]:
        """Create availability response for 'Not released yet'."""
        return {"times": [], "status": "Not released yet"}

    @staticmethod
    def sold_out() -> Dict[str, Any]:
        """Create availability response for 'Sold out'."""
        return {"times": [], "status": "Sold out"}

    @staticmethod
    def closed() -> Dict[str, Any]:
        """Create availability response for 'Closed'."""
        return {"times": [], "status": "Closed"}

    @staticmethod
    def unable_to_fetch() -> Dict[str, Any]:
        """Create availability response for 'Unable to fetch'."""
        return {"times": [], "status": "Unable to fetch"}

    @staticmethod
    def resy_unavailable() -> Dict[str, Any]:
        """Create availability response for 'Resy temporarily unavailable'."""
        return {"times": [], "status": "Resy temporarily unavailable"}


# =============================================================================
# Auto-reset VenueFactory counter
# =============================================================================

@pytest.fixture(autouse=True)
def reset_venue_counter():
    """Automatically reset VenueFactory counter before each test.
    
    This ensures venue IDs are predictable within each test,
    regardless of test execution order.
    """
    VenueFactory.reset_counter()
    yield
    # Optional: reset after test too for cleanliness
    VenueFactory.reset_counter()


# =============================================================================
# Mock Config Fixtures
# =============================================================================

@pytest.fixture
def mock_config():
    """Mock Resy config dict."""
    return {
        "api_key": "test_api_key",
        "token": "test_token",
        "payment_method_id": 12345,
        "email": "test@example.com",
        "password": None,
        "guest_id": None,
        "user_id": None,
        "first_name": None,
        "last_name": None,
        "mobile_number": None,
        "payment_methods": [],
        "legacy_token": None,
    }


# =============================================================================
# Filter Fixtures
# =============================================================================

@pytest.fixture
def empty_filters():
    """Empty filter set."""
    return {
        "cuisines": [],
        "price_ranges": [],
        "available_only": False,
        "not_released_only": False,
        "available_day": "",
        "available_party_size": 2,
        "desired_time": "",
        "offset": 0,
        "per_page": 20,
    }


@pytest.fixture
def cuisine_filter():
    """Filter with Italian cuisine only."""
    return {
        "cuisines": ["Italian"],
        "price_ranges": [],
        "available_only": False,
        "not_released_only": False,
        "available_day": "",
        "available_party_size": 2,
        "desired_time": "",
        "offset": 0,
        "per_page": 20,
    }


@pytest.fixture
def price_filter():
    """Filter with price range 4 only."""
    return {
        "cuisines": [],
        "price_ranges": [4],
        "available_only": False,
        "not_released_only": False,
        "available_day": "",
        "available_party_size": 2,
        "desired_time": "",
        "offset": 0,
        "per_page": 20,
    }


@pytest.fixture
def available_only_filter():
    """Filter for available_only with date and party size."""
    return {
        "cuisines": [],
        "price_ranges": [],
        "available_only": True,
        "not_released_only": False,
        "available_day": "2026-02-14",
        "available_party_size": 2,
        "desired_time": "",
        "offset": 0,
        "per_page": 20,
    }


@pytest.fixture
def not_released_only_filter():
    """Filter for not_released_only with date and party size."""
    return {
        "cuisines": [],
        "price_ranges": [],
        "available_only": False,
        "not_released_only": True,
        "available_day": "2026-02-14",
        "available_party_size": 2,
        "desired_time": "",
        "offset": 0,
        "per_page": 20,
    }


# =============================================================================
# Mock Search Function Fixtures
# =============================================================================

@pytest.fixture
def mock_search_func():
    """Create a mock search function that can be configured per test."""
    def _create_mock(pages_data: List[tuple]) -> callable:
        """
        Create a mock search function.
        
        Args:
            pages_data: List of (hits, total) tuples, one per page
        """
        page_num = [0]  # Use list to allow modification in closure
        
        def search_func(page: int):
            if page <= len(pages_data):
                hits, total = pages_data[page - 1]
                return hits, total
            return [], 0
        
        return search_func
    
    return _create_mock


# =============================================================================
# Geo Config Fixtures
# =============================================================================

@pytest.fixture
def geo_config_nyc():
    """NYC bounding box geo config."""
    return {
        "bounding_box": [40.7, -74.02, 40.8, -73.93]
    }


@pytest.fixture
def geo_config_radius():
    """Radius-based geo config."""
    return {
        "latitude": 40.7589,
        "longitude": -73.9851,
        "radius": 16100
    }
