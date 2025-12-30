# tests/test_selectors_simple_selector.py
import pytest
from dataclasses import dataclass
from datetime import datetime, date

from resy_client.selectors import SimpleSelector
from resy_client.errors import NoSlotsError


# Lightweight stand-ins to mimic the attributes SimpleSelector expects
class _Date:
    def __init__(self, start: datetime):
        self.start = start


class _Config:
    def __init__(self, type_: str):
        self.type = type_


class DummySlot:
    def __init__(self, start: datetime, type_: str):
        self.date = _Date(start)
        self.config = _Config(type_)


@dataclass
class DummyRequest:
    target_date: date
    ideal_hour: int
    ideal_minute: int
    window_hours: float
    preferred_type: str | None = None
    prefer_early: bool = True


def _resy_slots_2026_01_11():
    """
    Real slot times copied from your log payload for 2026-01-11.
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
    # Your selector assumes sorted ascending. This mirrors the log.
    return slots


def test_select_real_resy_slots_prefers_closest_after_ideal_within_window():
    """
    Ideal: 10:00 PM, window: ±2 hours, preferred_type: Dinner

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
    BUG (previous implementation):
      If every acceptable slot is BEFORE the ideal time (diff < 0),
      the loop never enters the `diff >= 0` return logic, and the function
      falls through and raises NoSlotsError even though `last_slot` was found.

    Using the real 2026-01-11 payload:
      Dinner slot exists at 5:00 PM.
      Set ideal to 6:00 PM with window ±1 hour.
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
        window_hours=1,        # ±1 hour => [5:00 PM, 7:00 PM]
        preferred_type="Dinner",
        prefer_early=True,
    )

    chosen = selector.select(slots, req)
    assert chosen.config.type == "Dinner"
    assert chosen.date.start == datetime(2026, 1, 11, 17, 0)  # 5:00 PM
