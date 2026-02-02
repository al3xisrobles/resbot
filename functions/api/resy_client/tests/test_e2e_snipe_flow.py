"""
End-to-end tests for the complete reservation snipe flow.

These tests simulate real-world scenarios by mocking the Resy API
and testing the full flow from reservation request to confirmation.

Tests cover:
- Happy path: successful reservation
- Parallel booking: racing multiple slots
- Retry scenarios: slots getting taken, network errors
- Edge cases: no slots available, all slots taken
- Timing-sensitive scenarios: high-demand drops
"""
import pytest
import responses
from datetime import datetime, date, timedelta

from resy_client.manager import ResyManager
from resy_client.models import (
    ResyConfig,
    ReservationRequest,
    ReservationRetriesConfig,
)
from resy_client.errors import NoSlotsError, ExhaustedRetriesError
from resy_client.constants import RESY_BASE_URL, ResyEndpoints


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def config():
    """Standard test configuration."""
    return ResyConfig(
        api_key="test_api_key",
        token="test_auth_token",
        payment_method_id=12345,
        retry_on_taken_slot=True,
    )


@pytest.fixture
def reservation_request():
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


def _build_slots_response(slots_data):
    """Helper to build a find slots API response."""
    slots = []
    for s in slots_data:
        slots.append({
            "config": {
                "id": s.get("id", 1132070),
                "type": s["type"],
                "token": s["token"],
            },
            "date": {
                "start": s["start"].isoformat(),
                "end": s["end"].isoformat(),
            },
        })
    return {
        "results": {
            "venues": [{"slots": slots}]
        }
    }


def _build_details_response(token_value="book_token_12345"):
    """Helper to build a details API response."""
    return {
        "book_token": {
            "value": token_value,
            "date_expires": (datetime.now() + timedelta(minutes=5)).isoformat(),
        }
    }


def _build_book_response(resy_token="resy_confirmation_abc123"):
    """Helper to build a book API response."""
    return {"resy_token": resy_token}


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestHappyPath:
    """Tests for successful reservation flows."""

    @responses.activate
    def test_complete_reservation_flow(self, config, reservation_request):
        """
        Full flow: find slots -> select best -> get token -> book -> success
        """
        # Mock find slots
        slots_data = [
            {
                "type": "Dining",
                "token": "rgs://resy/60058/4069767/2/2026-02-14/19:00:00/2/Dining",
                "start": datetime(2026, 2, 14, 19, 0),
                "end": datetime(2026, 2, 14, 20, 45),
            },
            {
                "type": "Dining",
                "token": "rgs://resy/60058/4069767/2/2026-02-14/19:30:00/2/Dining",
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
            {
                "type": "Dining",
                "token": "rgs://resy/60058/4069767/2/2026-02-14/20:00:00/2/Dining",
                "start": datetime(2026, 2, 14, 20, 0),
                "end": datetime(2026, 2, 14, 21, 45),
            },
        ]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        # Mock get booking token
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("booking_token_xyz"),
            status=200,
        )

        # Mock book slot
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("resy_confirm_123"),
            status=200,
        )

        # Execute
        manager = ResyManager.build(config)
        resy_token = manager.make_reservation(reservation_request)

        # Verify
        assert resy_token == "resy_confirm_123"
        assert len(responses.calls) == 3  # find, details, book

    @responses.activate
    def test_selects_closest_slot_to_ideal_time(self, config, reservation_request):
        """Should select 19:30 slot when ideal time is 19:30."""
        slots_data = [
            {
                "type": "Dining",
                "token": "token_1900",
                "start": datetime(2026, 2, 14, 19, 0),
                "end": datetime(2026, 2, 14, 20, 45),
            },
            {
                "type": "Dining",
                "token": "token_1930",  # This should be selected
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
            {
                "type": "Dining",
                "token": "token_2000",
                "start": datetime(2026, 2, 14, 20, 0),
                "end": datetime(2026, 2, 14, 21, 45),
            },
        ]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response(),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response(),
            status=200,
        )

        manager = ResyManager.build(config)
        manager.make_reservation(reservation_request)

        # Check that the details call used the 19:30 token
        details_call = responses.calls[1]
        assert "token_1930" in details_call.request.url


# =============================================================================
# Parallel Booking Tests
# =============================================================================

class TestParallelBooking:
    """Tests for parallel booking strategy."""

    @responses.activate
    def test_parallel_booking_first_success_wins(self, config, reservation_request):
        """Parallel booking should return on first success."""
        slots_data = [
            {
                "type": "Dining",
                "token": "token_1",
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
            {
                "type": "Dining",
                "token": "token_2",
                "start": datetime(2026, 2, 14, 19, 45),
                "end": datetime(2026, 2, 14, 21, 30),
            },
            {
                "type": "Dining",
                "token": "token_3",
                "start": datetime(2026, 2, 14, 20, 0),
                "end": datetime(2026, 2, 14, 21, 45),
            },
        ]

        # Find slots returns all 3
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        # Details endpoint - all succeed
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
                json=_build_details_response(),
                status=200,
            )

        # Book endpoint - first succeeds
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("parallel_success_token"),
            status=200,
        )
        # Others might not even be called due to parallel execution

        manager = ResyManager.build(config)
        result = manager.make_reservation_parallel(reservation_request, n_slots=3)

        assert result == "parallel_success_token"

    @responses.activate
    def test_parallel_booking_fallback_on_first_failure(self, config, reservation_request):
        """If first slot fails, should successfully book second."""
        slots_data = [
            {
                "type": "Dining",
                "token": "token_1",
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
            {
                "type": "Dining",
                "token": "token_2",
                "start": datetime(2026, 2, 14, 19, 45),
                "end": datetime(2026, 2, 14, 21, 30),
            },
        ]

        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        # Both get tokens
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("token_1_book"),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("token_2_book"),
            status=200,
        )

        # First book fails, second succeeds
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "Slot taken"},
            status=412,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("fallback_success"),
            status=200,
        )

        manager = ResyManager.build(config)
        result = manager.make_reservation_parallel(reservation_request, n_slots=2)

        assert result == "fallback_success"


# =============================================================================
# Retry Scenario Tests
# =============================================================================

class TestRetryScenarios:
    """Tests for retry logic in various failure scenarios."""

    @responses.activate
    def test_retry_on_no_slots_then_succeed(self, config, reservation_request):
        """Should retry when no slots, then succeed when slots appear."""
        # First call - no slots
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json={"results": {"venues": [{"slots": []}]}},
            status=200,
        )

        # Second call - slots available
        slots_data = [{
            "type": "Dining",
            "token": "token_retry",
            "start": datetime(2026, 2, 14, 19, 30),
            "end": datetime(2026, 2, 14, 21, 15),
        }]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response(),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("retry_success"),
            status=200,
        )

        manager = ResyManager.build(config)
        manager.retry_config = ReservationRetriesConfig(
            seconds_between_retries=0.001,
            n_retries=5,
        )

        result = manager.make_reservation_with_retries(reservation_request)

        assert result == "retry_success"
        # Should have called find twice
        find_calls = [c for c in responses.calls if ResyEndpoints.FIND.value in c.request.url]
        assert len(find_calls) == 2

    @responses.activate
    def test_retry_on_slot_taken_then_succeed(self, config, reservation_request):
        """Should retry when slot taken, then succeed with different slot."""
        slots_data = [
            {
                "type": "Dining",
                "token": "token_1",
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
            {
                "type": "Dining",
                "token": "token_2",
                "start": datetime(2026, 2, 14, 19, 45),
                "end": datetime(2026, 2, 14, 21, 30),
            },
        ]

        # Find returns same slots both times
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        # First attempt - get token, book fails
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("token_1_book"),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "Slot no longer available"},
            status=412,
        )

        # Second attempt - succeeds
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("token_2_book"),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("retry_after_taken"),
            status=200,
        )

        manager = ResyManager.build(config)
        manager.retry_config = ReservationRetriesConfig(
            seconds_between_retries=0.001,
            n_retries=5,
        )

        result = manager.make_reservation_with_retries(reservation_request)

        assert result == "retry_after_taken"

    @responses.activate
    def test_exhausted_retries_raises_error(self, config, reservation_request):
        """Should raise ExhaustedRetriesError after all retries fail."""
        # All calls return no slots
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
                json={"results": {"venues": [{"slots": []}]}},
                status=200,
            )

        manager = ResyManager.build(config)
        manager.retry_config = ReservationRetriesConfig(
            seconds_between_retries=0.001,
            n_retries=5,
        )

        with pytest.raises(ExhaustedRetriesError):
            manager.make_reservation_with_retries(reservation_request)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @responses.activate
    def test_no_slots_matching_type_preference(self, config):
        """Should fail when no slots match preferred type."""
        # Only Bar Table slots, but user wants Dining
        slots_data = [
            {
                "type": "Bar Table",
                "token": "bar_token",
                "start": datetime(2026, 2, 14, 19, 30),
                "end": datetime(2026, 2, 14, 21, 15),
            },
        ]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=2,
            prefer_early=True,
            preferred_type="Dining",  # No Dining slots available
            ideal_date=date(2026, 2, 14),
        )

        manager = ResyManager.build(config)

        with pytest.raises(NoSlotsError):
            manager.make_reservation(request)

    @responses.activate
    def test_slots_outside_time_window(self, config):
        """Should fail when slots exist but outside preferred window."""
        slots_data = [
            {
                "type": "Dining",
                "token": "late_token",
                "start": datetime(2026, 2, 14, 22, 0),  # Too late
                "end": datetime(2026, 2, 14, 23, 45),
            },
        ]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )

        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,  # [18:00, 20:00] - 22:00 is outside
            prefer_early=True,
            preferred_type="Dining",
            ideal_date=date(2026, 2, 14),
        )

        manager = ResyManager.build(config)

        with pytest.raises(NoSlotsError):
            manager.make_reservation(request)

    @responses.activate
    def test_single_slot_available(self, config, reservation_request):
        """Should successfully book when only one slot is available."""
        slots_data = [{
            "type": "Dining",
            "token": "only_slot",
            "start": datetime(2026, 2, 14, 19, 30),
            "end": datetime(2026, 2, 14, 21, 15),
        }]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response(),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("single_slot_success"),
            status=200,
        )

        manager = ResyManager.build(config)
        result = manager.make_reservation(reservation_request)

        assert result == "single_slot_success"


# =============================================================================
# High-Demand Scenario Tests
# =============================================================================

class TestHighDemandScenarios:
    """Tests simulating high-demand restaurant drops."""

    @responses.activate
    def test_valentines_day_drop_race(self, config):
        """
        Simulate Valentine's Day drop where slots disappear rapidly.
        First attempt: 36 slots
        Second attempt: 27 slots (9 taken)
        Third attempt: 15 slots (12 more taken)
        """
        # First find - many slots (slots every 15 min from 17:00 to 22:45)
        slots_1 = []
        for hour in range(17, 23):  # 17:00 to 22:45
            for minute in [0, 15, 30, 45]:
                slots_1.append({
                    "type": "Dining",
                    "token": f"token_{hour}_{minute}",
                    "start": datetime(2026, 2, 14, hour, minute),
                    "end": datetime(2026, 2, 14, hour + 1, minute + 45 if minute + 45 < 60 else (minute + 45) % 60),
                })
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_1),
            status=200,
        )

        # First book attempt fails
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response(),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "Slot taken"},
            status=412,
        )

        # Second find - fewer slots
        slots_2 = slots_1[:27]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_2),
            status=200,
        )

        # Second attempt succeeds
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response("winning_token"),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("valentines_success"),
            status=200,
        )

        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=3,
            prefer_early=True,
            preferred_type="Dining",
            ideal_date=date(2026, 2, 14),
        )

        manager = ResyManager.build(config)
        manager.retry_config = ReservationRetriesConfig(
            seconds_between_retries=0.001,
            n_retries=10,
        )

        result = manager.make_reservation_with_retries(request)

        assert result == "valentines_success"

    @responses.activate
    def test_all_prime_slots_taken_fallback_to_late(self, config):
        """When prime time (7-8 PM) is gone, should book late dinner."""
        # Only late slots available
        slots_data = [
            {
                "type": "Dining",
                "token": "late_1",
                "start": datetime(2026, 2, 14, 21, 30),
                "end": datetime(2026, 2, 14, 23, 15),
            },
            {
                "type": "Dining",
                "token": "late_2",
                "start": datetime(2026, 2, 14, 22, 0),
                "end": datetime(2026, 2, 14, 23, 45),
            },
        ]
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=_build_slots_response(slots_data),
            status=200,
        )
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=_build_details_response(),
            status=200,
        )
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=_build_book_response("late_dinner_booked"),
            status=200,
        )

        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=3,  # Wide window to catch late slots
            prefer_early=True,
            preferred_type="Dining",
            ideal_date=date(2026, 2, 14),
        )

        manager = ResyManager.build(config)
        result = manager.make_reservation(request)

        assert result == "late_dinner_booked"
        # Should have selected 21:30 (closer to 19:30 than 22:00)
        details_call = responses.calls[1]
        assert "late_1" in details_call.request.url
