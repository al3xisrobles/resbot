"""
Tests for slot selection logic.

Tests cover:
- SimpleSelector.select() - single best slot selection
- SimpleSelector.select_top_n() - top N slots for parallel booking
- Edge cases (exact match, only earlier slots, only later slots)
- Type filtering (Dining, Lunch, Bar Table)
- Window boundary conditions
- Tie-breaking logic (prefer_early vs prefer_late)
"""
import pytest
from dataclasses import dataclass
from datetime import datetime, date
from typing import List

from resy_client.selectors import SimpleSelector
from resy_client.errors import NoSlotsError


# =============================================================================
# Lightweight Test Objects
# =============================================================================

class _Date:
    """Lightweight slot date for unit tests."""
    def __init__(self, start: datetime):
        self.start = start


class _Config:
    """Lightweight slot config for unit tests."""
    def __init__(self, type_: str):
        self.type = type_


class DummySlot:
    """Lightweight slot for unit tests."""
    def __init__(self, start: datetime, type_: str):
        self.date = _Date(start)
        self.config = _Config(type_)


@dataclass
class DummyRequest:
    """Lightweight request for unit tests."""
    target_date: date
    ideal_hour: int
    ideal_minute: int
    window_hours: float
    preferred_type: str | None = None
    prefer_early: bool = True


# =============================================================================
# Test Data Factories
# =============================================================================

def _make_slot(hour: int, minute: int = 0, type_: str = "Dining", date_: date = None) -> DummySlot:
    """Create a test slot at the given time."""
    if date_ is None:
        date_ = date(2026, 2, 14)
    return DummySlot(datetime(date_.year, date_.month, date_.day, hour, minute), type_)


def _resy_slots_2026_01_11() -> List[DummySlot]:
    """
    Real slot times from log payload for 2026-01-11.
    (Lunch) 11:30, 11:45, 12:00, 13:15, 13:30, 13:45, 14:00
    (Dinner) 17:00, 22:00, 22:15, 22:30, 22:45, 23:00, 23:15, 23:30
    """
    d = date(2026, 1, 11)
    slots = [
        # Lunch
        DummySlot(datetime(d.year, d.month, d.day, 11, 30), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 11, 45), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 12, 0), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 13, 15), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 13, 30), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 13, 45), "Lunch"),
        DummySlot(datetime(d.year, d.month, d.day, 14, 0), "Lunch"),
        # Dinner
        DummySlot(datetime(d.year, d.month, d.day, 17, 0), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 22, 0), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 22, 15), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 22, 30), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 22, 45), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 23, 0), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 23, 15), "Dinner"),
        DummySlot(datetime(d.year, d.month, d.day, 23, 30), "Dinner"),
    ]
    return slots


def _valentines_day_slots() -> List[DummySlot]:
    """
    Realistic Valentine's Day slots - popular restaurant.
    Mix of Bar Table, Dining Room, and Dining types.
    """
    d = date(2026, 2, 14)
    return [
        # Lunch - Bar Table
        _make_slot(11, 45, "Bar Table", d),
        _make_slot(12, 0, "Bar Table", d),
        _make_slot(12, 15, "Bar Table", d),
        # Lunch - Dining Room
        _make_slot(11, 45, "Dining Room", d),
        _make_slot(12, 0, "Dining Room", d),
        _make_slot(12, 15, "Dining Room", d),
        _make_slot(12, 30, "Dining Room", d),
        _make_slot(12, 45, "Dining Room", d),
        # Dinner - Dining (prime time mostly gone)
        _make_slot(17, 0, "Dining", d),
        _make_slot(17, 15, "Dining", d),
        _make_slot(17, 30, "Dining", d),
        _make_slot(17, 45, "Dining", d),
        _make_slot(19, 30, "Dining", d),  # One prime slot left
        # Late dinner
        _make_slot(21, 0, "Dining", d),
        _make_slot(21, 15, "Dining", d),
        _make_slot(21, 30, "Dining", d),
        _make_slot(21, 45, "Dining", d),
        _make_slot(22, 0, "Dining", d),
        _make_slot(22, 15, "Dining", d),
        _make_slot(22, 30, "Dining", d),
    ]


# =============================================================================
# Original Tests (preserved from existing file)
# =============================================================================

def test_select_real_resy_slots_prefers_closest_after_ideal_within_window():
    """
    Ideal: 10:00 PM, window: +/-2 hours, preferred_type: Dinner

    Candidates in window:
      22:00, 22:15, 22:30, 22:45, 23:00, 23:15, 23:30
    Exact match exists at 22:00, so the selector should pick 22:00.
    """
    selector = SimpleSelector()
    slots = _resy_slots_2026_01_11()
    req = DummyRequest(
        target_date=date(2026, 1, 11),
        ideal_hour=22,
        ideal_minute=0,
        window_hours=2,
        preferred_type="Dinner",
        prefer_early=True,
    )

    chosen = selector.select(slots, req)
    assert chosen.config.type == "Dinner"
    assert chosen.date.start == datetime(2026, 1, 11, 22, 0)


def test_select_exact_match_returns_immediately_even_if_other_slots_exist():
    """
    Add an exact ideal-time slot and ensure it gets selected.
    """
    selector = SimpleSelector()
    slots = _resy_slots_2026_01_11()

    # Put an exact match at 7:00 PM (19:00) in the correct sorted position.
    exact = DummySlot(datetime(2026, 1, 11, 19, 0), "Dinner")
    slots = sorted(slots + [exact], key=lambda s: s.date.start)

    req = DummyRequest(
        target_date=date(2026, 1, 11),
        ideal_hour=19,
        ideal_minute=0,
        window_hours=3,
        preferred_type="Dinner",
        prefer_early=True,
    )

    chosen = selector.select(slots, req)
    assert chosen.config.type == "Dinner"
    assert chosen.date.start == datetime(2026, 1, 11, 19, 0)


def test_select_only_earlier_slots_in_window_returns_best_earlier_instead_of_error():
    """
    BUG FIX TEST (previous implementation):
      If every acceptable slot is BEFORE the ideal time (diff < 0),
      the loop never enters the `diff >= 0` return logic, and the function
      falls through and raises NoSlotsError even though `last_slot` was found.

    Using the real 2026-01-11 payload:
      Dinner slot exists at 5:00 PM.
      Set ideal to 6:00 PM with window +/-1 hour.
      The only Dinner slot in-window is 5:00 PM (earlier).
      Correct behavior: return 5:00 PM.
      Previous behavior: raised NoSlotsError.
    """
    selector = SimpleSelector()
    slots = _resy_slots_2026_01_11()

    req = DummyRequest(
        target_date=date(2026, 1, 11),
        ideal_hour=18,         # 6:00 PM
        ideal_minute=0,
        window_hours=1,        # +/-1 hour => [5:00 PM, 7:00 PM]
        preferred_type="Dinner",
        prefer_early=True,
    )

    chosen = selector.select(slots, req)
    assert chosen.config.type == "Dinner"
    assert chosen.date.start == datetime(2026, 1, 11, 17, 0)  # 5:00 PM


# =============================================================================
# SimpleSelector.select() Tests - Extended
# =============================================================================

class TestSimpleSelectorSelect:
    """Tests for single best slot selection."""

    def test_select_closest_to_ideal(self):
        """Should select slot closest to ideal time."""
        selector = SimpleSelector()
        slots = _resy_slots_2026_01_11()

        req = DummyRequest(
            target_date=date(2026, 1, 11),
            ideal_hour=22,
            ideal_minute=0,
            window_hours=2,
            preferred_type="Dinner",
        )

        chosen = selector.select(slots, req)
        assert chosen.date.start == datetime(2026, 1, 11, 22, 0)

    def test_select_respects_type_filter(self):
        """Should only select slots matching preferred_type."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Bar Table", d),
            _make_slot(19, 15, "Bar Table", d),
            _make_slot(19, 30, "Dining", d),  # Only Dining option
            _make_slot(19, 45, "Bar Table", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            preferred_type="Dining",
        )

        chosen = selector.select(slots, req)
        assert chosen.config.type == "Dining"
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 30

    def test_select_no_type_filter_picks_any(self):
        """No preferred_type should allow any slot type."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Bar Table", d),
            _make_slot(19, 30, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            preferred_type=None,  # No preference
        )

        chosen = selector.select(slots, req)
        # Should pick the closest (19:00 Bar Table)
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 0

    def test_select_only_later_slots_in_window(self):
        """When all acceptable slots are AFTER ideal time."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(20, 0, "Dining", d),
            _make_slot(20, 30, "Dining", d),
            _make_slot(21, 0, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=2,  # [5:00 PM, 9:00 PM]
            preferred_type="Dining",
        )

        chosen = selector.select(slots, req)
        # Should pick 8:00 PM (closest to 7:00 PM)
        assert chosen.date.start.hour == 20
        assert chosen.date.start.minute == 0

    def test_select_no_slots_in_window_raises_error(self):
        """No slots within window should raise NoSlotsError."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(12, 0, "Lunch", d),
            _make_slot(22, 0, "Dinner", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,  # [6:00 PM, 8:00 PM] - no slots here
            preferred_type=None,
        )

        with pytest.raises(NoSlotsError):
            selector.select(slots, req)

    def test_select_no_slots_matching_type_raises_error(self):
        """No slots matching type filter should raise NoSlotsError."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Bar Table", d),
            _make_slot(19, 30, "Bar Table", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            preferred_type="Dining",  # No Dining slots exist
        )

        with pytest.raises(NoSlotsError):
            selector.select(slots, req)

    def test_select_empty_slots_raises_error(self):
        """Empty slot list should raise NoSlotsError."""
        selector = SimpleSelector()

        req = DummyRequest(
            target_date=date(2026, 2, 14),
            ideal_hour=19,
            ideal_minute=0,
            window_hours=2,
        )

        with pytest.raises(NoSlotsError):
            selector.select([], req)

    def test_select_prefer_early_tiebreaker(self):
        """When prefer_early=True, should pick earlier slot on tie."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        # Two slots equidistant from 19:00
        slots = [
            _make_slot(18, 30, "Dining", d),  # 30 min earlier
            _make_slot(19, 30, "Dining", d),  # 30 min later
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            prefer_early=True,
        )

        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 18
        assert chosen.date.start.minute == 30

    def test_select_prefer_late_tiebreaker(self):
        """When prefer_early=False, should pick later slot on tie."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(18, 30, "Dining", d),
            _make_slot(19, 30, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
            prefer_early=False,
        )

        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 30

    def test_select_window_boundary_inclusive(self):
        """Slots exactly at window boundaries should be included."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(18, 0, "Dining", d),  # Exactly at min boundary
            _make_slot(19, 0, "Dining", d),  # Ideal
            _make_slot(20, 0, "Dining", d),  # Exactly at max boundary
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,  # [18:00, 20:00]
        )

        # All three should be valid; should pick 19:00 (exact match)
        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 19

    def test_select_with_minutes_in_ideal_time(self):
        """Should handle non-zero minutes in ideal time."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Dining", d),
            _make_slot(19, 15, "Dining", d),
            _make_slot(19, 30, "Dining", d),  # Closest to 19:25
            _make_slot(19, 45, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=25,  # 7:25 PM
            window_hours=1,
        )

        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 30

    def test_select_single_slot_in_window(self):
        """Should select the only slot if it's in window."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [_make_slot(19, 30, "Dining", d)]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
        )

        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 30

    def test_select_fractional_window_hours(self):
        """Should handle fractional window hours."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(18, 45, "Dining", d),  # Just inside 30min window
            _make_slot(19, 0, "Dining", d),
            _make_slot(19, 15, "Dining", d),  # Just inside 30min window
            _make_slot(19, 45, "Dining", d),  # Outside window
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=0.5,  # 30 minutes [18:30, 19:30]
        )

        chosen = selector.select(slots, req)
        # Should pick 19:00 (exact match)
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 0


# =============================================================================
# SimpleSelector.select_top_n() Tests
# =============================================================================

class TestSimpleSelectorSelectTopN:
    """Tests for top N slot selection (for parallel booking)."""

    def test_select_top_n_returns_n_slots(self):
        """Should return exactly N slots when available."""
        selector = SimpleSelector()
        slots = _valentines_day_slots()

        req = DummyRequest(
            target_date=date(2026, 2, 14),
            ideal_hour=19,
            ideal_minute=30,
            window_hours=3,
            preferred_type="Dining",
        )

        top = selector.select_top_n(slots, req, n=3)
        assert len(top) == 3

    def test_select_top_n_returns_fewer_if_not_enough(self):
        """Should return fewer than N if not enough slots available."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Dining", d),
            _make_slot(19, 30, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
        )

        top = selector.select_top_n(slots, req, n=5)
        assert len(top) == 2

    def test_select_top_n_ordered_by_proximity(self):
        """Results should be ordered by distance from ideal time."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(17, 0, "Dining", d),   # 2.5h away
            _make_slot(18, 30, "Dining", d),  # 1h away
            _make_slot(19, 30, "Dining", d),  # Exact match
            _make_slot(20, 30, "Dining", d),  # 1h away
            _make_slot(22, 0, "Dining", d),   # 2.5h away
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=3,
        )

        top = selector.select_top_n(slots, req, n=3)

        # First should be 19:30 (exact match)
        assert top[0].date.start.hour == 19
        assert top[0].date.start.minute == 30

    def test_select_top_n_respects_type_filter(self):
        """Should only include slots matching preferred_type."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Bar Table", d),
            _make_slot(19, 15, "Dining", d),
            _make_slot(19, 30, "Bar Table", d),
            _make_slot(19, 45, "Dining", d),
            _make_slot(20, 0, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,
            preferred_type="Dining",
        )

        top = selector.select_top_n(slots, req, n=5)

        # Should only have Dining slots
        assert all(s.config.type == "Dining" for s in top)
        assert len(top) == 3

    def test_select_top_n_respects_window(self):
        """Should only include slots within window."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(12, 0, "Dining", d),  # Outside window
            _make_slot(19, 0, "Dining", d),  # In window
            _make_slot(19, 30, "Dining", d), # In window
            _make_slot(20, 0, "Dining", d),  # In window
            _make_slot(23, 0, "Dining", d),  # Outside window
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,  # [18:30, 20:30]
        )

        top = selector.select_top_n(slots, req, n=5)

        assert len(top) == 3
        # Verify all are within window
        for s in top:
            assert 18 <= s.date.start.hour <= 21

    def test_select_top_n_no_slots_raises_error(self):
        """No matching slots should raise NoSlotsError."""
        selector = SimpleSelector()

        req = DummyRequest(
            target_date=date(2026, 2, 14),
            ideal_hour=19,
            ideal_minute=0,
            window_hours=1,
        )

        with pytest.raises(NoSlotsError):
            selector.select_top_n([], req, n=3)

    def test_select_top_n_with_single_slot(self):
        """Should handle single slot correctly."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [_make_slot(19, 30, "Dining", d)]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,
        )

        top = selector.select_top_n(slots, req, n=3)
        assert len(top) == 1
        assert top[0].date.start.hour == 19

    def test_select_top_n_default_is_3(self):
        """Default n should be 3."""
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(19, 0, "Dining", d),
            _make_slot(19, 15, "Dining", d),
            _make_slot(19, 30, "Dining", d),
            _make_slot(19, 45, "Dining", d),
            _make_slot(20, 0, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,
        )

        top = selector.select_top_n(slots, req)  # No n specified
        assert len(top) == 3


# =============================================================================
# Edge Cases and Real-World Scenarios
# =============================================================================

class TestRealWorldScenarios:
    """Tests based on real-world scenarios from production logs."""

    def test_valentines_day_prime_time_hunt(self):
        """
        Scenario: Valentine's Day, user wants 7:30 PM Dining.
        Most prime slots are gone, only 19:30 remains in that window.
        """
        selector = SimpleSelector()
        slots = _valentines_day_slots()

        req = DummyRequest(
            target_date=date(2026, 2, 14),
            ideal_hour=19,
            ideal_minute=30,
            window_hours=1,  # [18:30, 20:30]
            preferred_type="Dining",
        )

        chosen = selector.select(slots, req)
        # Should get the 19:30 Dining slot
        assert chosen.date.start.hour == 19
        assert chosen.date.start.minute == 30
        assert chosen.config.type == "Dining"

    def test_fallback_to_late_dinner(self):
        """
        Scenario: Prime time sold out, user has wide window.
        Should fall back to closest available (late dinner).
        """
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        # Only late slots available
        slots = [
            _make_slot(21, 0, "Dining", d),
            _make_slot(21, 30, "Dining", d),
            _make_slot(22, 0, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=3,  # Wide window [16:30, 22:30]
            preferred_type="Dining",
        )

        chosen = selector.select(slots, req)
        # Should pick 21:00 (closest to 19:30)
        assert chosen.date.start.hour == 21
        assert chosen.date.start.minute == 0

    def test_lunch_to_early_dinner_window(self):
        """
        Scenario: User flexible between late lunch and early dinner.
        """
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        slots = [
            _make_slot(13, 30, "Lunch", d),
            _make_slot(14, 0, "Lunch", d),
            _make_slot(17, 0, "Dining", d),
            _make_slot(17, 30, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=15,
            ideal_minute=0,
            window_hours=2,  # [13:00, 17:00]
            preferred_type=None,  # Accept any
        )

        # 14:00 and 17:00 are equidistant from 15:00
        # With prefer_early=True (default), should pick 14:00
        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 14

    def test_parallel_booking_top_3_for_snipe(self):
        """
        Scenario: Snipe bot needs top 3 slots for parallel booking.
        """
        selector = SimpleSelector()
        slots = _valentines_day_slots()

        req = DummyRequest(
            target_date=date(2026, 2, 14),
            ideal_hour=19,
            ideal_minute=30,
            window_hours=2,
            preferred_type="Dining",
        )

        top = selector.select_top_n(slots, req, n=3)

        assert len(top) == 3
        # All should be Dining type
        assert all(s.config.type == "Dining" for s in top)
        # First should be closest to 19:30
        assert top[0].date.start.hour == 19 and top[0].date.start.minute == 30

    def test_high_demand_scenario_all_prime_taken(self):
        """
        Scenario: All prime time slots taken, only early and late remain.
        """
        selector = SimpleSelector()
        d = date(2026, 2, 14)
        # Gap between 14:30 and 21:30
        slots = [
            _make_slot(12, 0, "Dining", d),
            _make_slot(12, 30, "Dining", d),
            _make_slot(13, 0, "Dining", d),
            _make_slot(13, 30, "Dining", d),
            _make_slot(14, 0, "Dining", d),
            _make_slot(14, 30, "Dining", d),
            # Big gap - prime time gone
            _make_slot(21, 30, "Dining", d),
            _make_slot(22, 0, "Dining", d),
            _make_slot(22, 30, "Dining", d),
        ]

        req = DummyRequest(
            target_date=d,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=5,  # Wide window to catch something
        )

        # Should pick 21:30 (2.5 hours from 19:00) over 14:30 (4.5 hours from 19:00)
        chosen = selector.select(slots, req)
        assert chosen.date.start.hour == 21
        assert chosen.date.start.minute == 30


class TestAbstractSelectorInterface:
    """Tests for AbstractSelector base class behavior."""

    def test_simple_selector_has_select_method(self):
        """SimpleSelector should have select method."""
        selector = SimpleSelector()
        assert hasattr(selector, "select")
        assert callable(selector.select)

    def test_simple_selector_has_select_top_n_method(self):
        """SimpleSelector should have select_top_n method."""
        selector = SimpleSelector()
        assert hasattr(selector, "select_top_n")
        assert callable(selector.select_top_n)
