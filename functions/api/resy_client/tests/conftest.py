"""
Shared pytest fixtures for resy_client tests.

This module provides reusable fixtures for:
- Mock Resy API responses
- Test data factories
- Configuration objects
- HTTP mocking setup
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import pytest
import responses
from resy_client.constants import RESY_BASE_URL, ResyEndpoints
from resy_client.models import (ReservationRequest, ResyConfig, Slot,
                                SlotConfig, SlotDate)

# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def resy_config() -> ResyConfig:
    """Standard Resy configuration for tests."""
    return ResyConfig(
        api_key="test_api_key_12345",
        token="test_token_abcdef",
        payment_method_id=12345,
        email="test@example.com",
        password="testpassword123",
        retry_on_taken_slot=True,
    )


@pytest.fixture
def resy_config_no_retry() -> ResyConfig:
    """Resy configuration with retry disabled."""
    return ResyConfig(
        api_key="test_api_key_12345",
        token="test_token_abcdef",
        payment_method_id=12345,
        retry_on_taken_slot=False,
    )


# =============================================================================
# Reservation Request Fixtures
# =============================================================================

@pytest.fixture
def reservation_request_dinner() -> ReservationRequest:
    """Standard dinner reservation request."""
    return ReservationRequest(
        venue_id="60058",
        party_size=2,
        ideal_hour=19,
        ideal_minute=30,
        window_hours=2,
        prefer_early=True,
        preferred_type="Dining",
        ideal_date=date(2026, 2, 14),
    )


@pytest.fixture
def reservation_request_lunch() -> ReservationRequest:
    """Standard lunch reservation request."""
    return ReservationRequest(
        venue_id="60058",
        party_size=4,
        ideal_hour=12,
        ideal_minute=0,
        window_hours=1,
        prefer_early=False,
        preferred_type="Lunch",
        ideal_date=date(2026, 2, 14),
    )


@pytest.fixture
def reservation_request_any_type() -> ReservationRequest:
    """Reservation request without type preference."""
    return ReservationRequest(
        venue_id="60058",
        party_size=2,
        ideal_hour=19,
        ideal_minute=0,
        window_hours=3,
        prefer_early=True,
        preferred_type=None,
        ideal_date=date(2026, 2, 14),
    )


@pytest.fixture
def reservation_request_days_in_advance() -> ReservationRequest:
    """Reservation request using days_in_advance instead of ideal_date."""
    return ReservationRequest(
        venue_id="60058",
        party_size=2,
        ideal_hour=19,
        ideal_minute=0,
        window_hours=2,
        prefer_early=True,
        days_in_advance=14,
    )


# =============================================================================
# Slot Factory and Fixtures
# =============================================================================

class SlotFactory:
    """Factory for creating test Slot objects."""

    @staticmethod
    def create(
        start_hour: int,
        start_minute: int = 0,
        slot_type: str = "Dining",
        slot_id: int = 1132061,
        token_prefix: str = "rgs://resy/60058/4069767",
        date_obj: date = None,
        duration_minutes: int = 105,
    ) -> Slot:
        """Create a Slot with the given parameters."""
        if date_obj is None:
            date_obj = date(2026, 2, 14)

        start = datetime(date_obj.year, date_obj.month, date_obj.day, start_hour, start_minute)
        end = start + timedelta(minutes=duration_minutes)

        token = f"{token_prefix}/2/{date_obj.isoformat()}/{date_obj.isoformat()}/{start_hour:02d}:{start_minute:02d}:00/2/{slot_type}"

        return Slot(
            config=SlotConfig(id=slot_id, type=slot_type, token=token),
            date=SlotDate(start=start, end=end),
        )

    @staticmethod
    def create_batch(
        times: List[tuple],
        slot_type: str = "Dining",
        date_obj: date = None,
    ) -> List[Slot]:
        """
        Create multiple slots from a list of (hour, minute) tuples.

        Args:
            times: List of (hour, minute) tuples
            slot_type: Type for all slots
            date_obj: Date for all slots
        """
        return [
            SlotFactory.create(hour, minute, slot_type=slot_type, date_obj=date_obj)
            for hour, minute in times
        ]


@pytest.fixture
def slot_factory() -> SlotFactory:
    """Provide SlotFactory for tests."""
    return SlotFactory()


@pytest.fixture
def sample_dinner_slots() -> List[Slot]:
    """Sample dinner slots for Valentine's Day 2026."""
    d = date(2026, 2, 14)
    return [
        SlotFactory.create(17, 0, "Dining", date_obj=d),
        SlotFactory.create(17, 15, "Dining", date_obj=d),
        SlotFactory.create(17, 30, "Dining", date_obj=d),
        SlotFactory.create(17, 45, "Dining", date_obj=d),
        SlotFactory.create(19, 30, "Dining", date_obj=d),
        SlotFactory.create(21, 0, "Dining", date_obj=d),
        SlotFactory.create(21, 15, "Dining", date_obj=d),
        SlotFactory.create(21, 30, "Dining", date_obj=d),
        SlotFactory.create(21, 45, "Dining", date_obj=d),
        SlotFactory.create(22, 0, "Dining", date_obj=d),
        SlotFactory.create(22, 15, "Dining", date_obj=d),
        SlotFactory.create(22, 30, "Dining", date_obj=d),
    ]


@pytest.fixture
def sample_lunch_slots() -> List[Slot]:
    """Sample lunch slots."""
    d = date(2026, 2, 14)
    return [
        SlotFactory.create(11, 45, "Lunch", date_obj=d),
        SlotFactory.create(12, 0, "Lunch", date_obj=d),
        SlotFactory.create(12, 15, "Lunch", date_obj=d),
        SlotFactory.create(12, 30, "Lunch", date_obj=d),
        SlotFactory.create(12, 45, "Lunch", date_obj=d),
        SlotFactory.create(13, 0, "Lunch", date_obj=d),
        SlotFactory.create(13, 15, "Lunch", date_obj=d),
        SlotFactory.create(13, 30, "Lunch", date_obj=d),
        SlotFactory.create(13, 45, "Lunch", date_obj=d),
        SlotFactory.create(14, 0, "Lunch", date_obj=d),
    ]


@pytest.fixture
def sample_bar_slots() -> List[Slot]:
    """Sample bar table slots."""
    d = date(2026, 2, 14)
    return [
        SlotFactory.create(11, 45, "Bar Table", date_obj=d),
        SlotFactory.create(12, 0, "Bar Table", date_obj=d),
        SlotFactory.create(12, 15, "Bar Table", date_obj=d),
        SlotFactory.create(12, 30, "Bar Table", date_obj=d),
        SlotFactory.create(12, 45, "Bar Table", date_obj=d),
        SlotFactory.create(13, 0, "Bar Table", date_obj=d),
    ]


@pytest.fixture
def sample_mixed_slots(sample_dinner_slots_list, sample_lunch_slots_list, sample_bar_slots_list) -> List[Slot]:
    """Combined slots of all types, sorted by start time."""
    all_slots = sample_lunch_slots_list + sample_bar_slots_list + sample_dinner_slots_list
    return sorted(all_slots, key=lambda s: s.date.start)


@pytest.fixture
def empty_slots() -> List[Slot]:
    """Empty slot list for testing no-availability scenarios."""
    return []


# =============================================================================
# API Response Fixtures
# =============================================================================

@pytest.fixture
def find_response_with_slots(sample_dinner_slots) -> Dict[str, Any]:
    """Mock API response for find endpoint with slots."""
    slots_data = [
        {
            "config": {
                "id": s.config.id,
                "type": s.config.type,
                "token": s.config.token,
            },
            "date": {
                "start": s.date.start.isoformat(),
                "end": s.date.end.isoformat(),
            },
        }
        for s in sample_dinner_slots
    ]

    return {
        "results": {
            "venues": [
                {
                    "slots": slots_data,
                    "venue": {"id": {"resy": 60058}},
                }
            ]
        }
    }


@pytest.fixture
def find_response_empty() -> Dict[str, Any]:
    """Mock API response for find endpoint with no slots."""
    return {
        "results": {
            "venues": [
                {
                    "slots": [],
                    "venue": {"id": {"resy": 60058}},
                }
            ]
        }
    }


@pytest.fixture
def details_response() -> Dict[str, Any]:
    """Mock API response for details endpoint."""
    return {
        "book_token": {
            "date_expires": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "value": "test_book_token_value_12345",
        }
    }


@pytest.fixture
def book_response_success() -> Dict[str, Any]:
    """Mock API response for successful booking."""
    return {
        "resy_token": "resy_confirmation_token_abc123",
    }


@pytest.fixture
def venue_search_response() -> Dict[str, Any]:
    """Mock API response for venue search."""
    return {
        "search": {
            "hits": [
                {
                    "_source": {
                        "id": {"resy": 60058},
                        "name": "Carbone",
                        "locality": "New York",
                        "region": "NY",
                        "neighborhood": "Greenwich Village",
                        "type": "Italian",
                        "price_range_id": 4,
                    }
                },
                {
                    "_source": {
                        "id": {"resy": 60059},
                        "name": "Carbone Miami",
                        "locality": "Miami",
                        "region": "FL",
                        "neighborhood": "South Beach",
                        "type": "Italian",
                        "price_range_id": 4,
                    }
                },
            ]
        }
    }


# =============================================================================
# HTTP Mocking Fixtures
# =============================================================================

@pytest.fixture
def mock_resy_api():
    """
    Context manager that activates responses mocking.
    Use this to add custom responses in individual tests.
    """
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_successful_booking_flow(
    mock_resy_api,
    find_response_with_slots,
    details_response,
    book_response_success,
):
    """
    Pre-configured mock for a complete successful booking flow.
    Sets up find -> details -> book with success responses.
    """
    # Find slots
    mock_resy_api.add(
        responses.POST,
        f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
        json=find_response_with_slots,
        status=200,
    )

    # Get booking token
    mock_resy_api.add(
        responses.GET,
        f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
        json=details_response,
        status=200,
    )

    # Book slot
    mock_resy_api.add(
        responses.POST,
        f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
        json=book_response_success,
        status=200,
    )

    return mock_resy_api


@pytest.fixture
def mock_no_slots_available(mock_resy_api, find_response_empty):
    """Mock for when no slots are available."""
    mock_resy_api.add(
        responses.POST,
        f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
        json=find_response_empty,
        status=200,
    )
    return mock_resy_api


# =============================================================================
# Dummy/Lightweight Test Objects (for unit tests without Pydantic overhead)
# =============================================================================

@dataclass
class DummySlotDate:
    """Lightweight slot date for unit tests."""
    start: datetime


@dataclass
class DummySlotConfig:
    """Lightweight slot config for unit tests."""
    type: str
    id: int = 1
    token: str = "test_token"


@dataclass
class DummySlot:
    """Lightweight slot for unit tests."""
    date: DummySlotDate
    config: DummySlotConfig

    @classmethod
    def create(cls, hour: int, minute: int = 0, slot_type: str = "Dining", date_obj: date | None = None):
        if date_obj is None:
            date_obj = date(2026, 2, 14)
        start = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
        return cls(
            date=DummySlotDate(start=start),
            config=DummySlotConfig(type=slot_type),
        )


@dataclass
class DummyRequest:
    """Lightweight request for unit tests."""
    target_date: date
    ideal_hour: int
    ideal_minute: int
    window_hours: float
    preferred_type: str | None = None
    prefer_early: bool = True


@pytest.fixture
def dummy_slot_class():
    """Provide DummySlot class for tests."""
    return DummySlot


@pytest.fixture
def dummy_request_class():
    """Provide DummyRequest class for tests."""
    return DummyRequest
