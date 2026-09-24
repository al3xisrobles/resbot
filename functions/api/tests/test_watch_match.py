"""
Unit tests for cancellation watch decisions: what counts as an opening, which
slots a watch may book, and who gets a contested slot.
"""
import datetime as dt
import json
import pathlib

from api.resy_client.models import Slot
from api.watch_match import assign_slots, in_range, is_release, new_openings, slot_key, slot_quantities

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "resy"


def make_slot(hhmm: str, seating: str = "Dining Room", day: str = "2026-09-26", quantity: int = 1) -> Slot:
    start = dt.datetime.fromisoformat(f"{day} {hhmm}:00")
    return Slot(
        config={"id": 1, "type": seating, "token": f"tok-{hhmm}-{seating}"},
        date={"start": start, "end": start + dt.timedelta(hours=2)},
        quantity=quantity,
    )


def make_watch(job_id: str, start: str, end: str, created_minute: int = 0, seating=None) -> dict:
    return {
        "jobId": job_id,
        "rangeStart": start,
        "rangeEnd": end,
        "seatingType": seating,
        "createdAt": dt.datetime(2026, 9, 20, 12, created_minute, tzinfo=dt.timezone.utc),
    }


class TestSlotKey:
    def test_key_from_real_payload(self):
        """Keys must come out of real /4/find slots, not only hand-built ones."""
        body = json.loads((FIXTURES / "find_available.json").read_text())
        slots = [Slot(**s) for s in body["results"]["venues"][0]["slots"]]
        keys = [slot_key(s) for s in slots]
        assert keys and all("|" in k for k in keys)
        assert len(set(keys)) == len(keys)

    def test_seating_type_is_part_of_identity(self):
        """A bar seat opening at 7pm is a different table than a dining room seat at 7pm."""
        assert slot_key(make_slot("19:00", "Bar")) != slot_key(make_slot("19:00", "Dining Room"))


class TestNewOpenings:
    def test_first_poll_of_a_date_is_a_baseline(self):
        """Slots already open when we start watching are not reported as openings."""
        assert not new_openings(None, {"19:00|Dining Room": 1})

    def test_old_list_snapshot_is_a_baseline(self):
        """Snapshots written before quantities were tracked must not read as a burst of openings."""
        assert not new_openings(["19:00|Dining Room"], {"19:00|Dining Room": 2, "21:00|Bar": 1})

    def test_slot_on_a_previously_sold_out_date_is_an_opening(self):
        assert new_openings({}, {"19:00|Dining Room": 1}) == ["19:00|Dining Room"]

    def test_only_new_keys_are_reported(self):
        assert new_openings({"19:00|Dining Room": 1}, {"19:00|Dining Room": 1, "21:00|Bar": 1}) == ["21:00|Bar"]

    def test_more_tables_at_a_shown_time_is_an_opening(self):
        """A cancellation at a time that still had a table left only shows up as a higher quantity."""
        assert new_openings({"19:00|Dining Room": 1}, {"19:00|Dining Room": 2}) == ["19:00|Dining Room"]

    def test_fewer_tables_or_removed_slots_are_not_openings(self):
        assert not new_openings({"19:00|Dining Room": 2}, {"19:00|Dining Room": 1})
        assert not new_openings({"19:00|Dining Room": 1}, {})


class TestSlotQuantities:
    def test_quantities_from_real_payload(self):
        body = json.loads((FIXTURES / "find_available.json").read_text())
        slots = [Slot(**s) for s in body["results"]["venues"][0]["slots"]]
        assert slot_quantities(slots) == {"21:15|Dining Room": 1, "21:30|Dining Room": 2}

    def test_missing_quantity_counts_as_one(self):
        slot = make_slot("19:00")
        slot.model_extra.pop("quantity")
        assert slot_quantities([slot]) == {"19:00|Dining Room": 1}


class TestInRange:
    def test_both_ends_are_inclusive(self):
        """'Anywhere from 5 to 9pm' must include 5:00 and 9:00 exactly."""
        assert in_range(make_slot("17:00"), "17:00", "21:00")
        assert in_range(make_slot("21:00"), "17:00", "21:00")

    def test_one_minute_outside_is_never_booked(self):
        assert not in_range(make_slot("16:59"), "17:00", "21:00")
        assert not in_range(make_slot("21:01"), "17:00", "21:00")


class TestAssignSlots:
    def test_oldest_watch_gets_a_contested_slot(self):
        """First come, first served: the watch created first wins the only opening."""
        older = make_watch("older", "17:00", "21:00", created_minute=1)
        newer = make_watch("newer", "17:00", "21:00", created_minute=5)
        assert assign_slots([newer, older], [make_slot("19:00")]) == {"older": make_slot("19:00")}

    def test_each_slot_goes_to_one_watch(self):
        """Two openings serve two watchers, never one watcher twice."""
        a = make_watch("a", "17:00", "21:00", created_minute=1)
        b = make_watch("b", "17:00", "21:00", created_minute=2)
        result = assign_slots([a, b], [make_slot("19:00"), make_slot("20:00")])
        assert slot_key(result["a"]) == "19:00|Dining Room"
        assert slot_key(result["b"]) == "20:00|Dining Room"

    def test_older_watch_takes_earliest_even_if_newer_only_fits_that_slot(self):
        """Arrival order beats packing: we never hand an older watch's slot to a newer one."""
        older = make_watch("older", "17:00", "21:00", created_minute=1)
        narrow = make_watch("narrow", "19:00", "19:00", created_minute=2)
        result = assign_slots([older, narrow], [make_slot("19:00"), make_slot("20:00")])
        assert slot_key(result["older"]) == "19:00|Dining Room"
        assert "narrow" not in result

    def test_slot_with_two_tables_serves_two_watches(self):
        a = make_watch("a", "17:00", "21:00", created_minute=1)
        b = make_watch("b", "17:00", "21:00", created_minute=2)
        c = make_watch("c", "17:00", "21:00", created_minute=3)
        result = assign_slots([a, b, c], [make_slot("19:00", quantity=2)])
        assert sorted(result) == ["a", "b"]

    def test_seating_type_filter(self):
        bar_only = make_watch("bar", "17:00", "21:00", seating="Bar")
        assert not assign_slots([bar_only], [make_slot("19:00", "Dining Room")])
        assert assign_slots([bar_only], [make_slot("19:00", "Bar")])

    def test_slot_outside_every_range_is_unassigned(self):
        assert not assign_slots([make_watch("a", "17:00", "18:00")], [make_slot("22:00")])

    def test_watch_without_created_at_sorts_last(self):
        """A watch whose server timestamp has not resolved yet must not jump the queue."""
        stamped = make_watch("stamped", "17:00", "21:00")
        unstamped = {**make_watch("unstamped", "17:00", "21:00"), "createdAt": None}
        assert list(assign_slots([unstamped, stamped], [make_slot("19:00")])) == ["stamped"]


class TestIsRelease:
    venue = {"dropTimeDiscovery": {"actualDropTime": "09:00:04"}}

    def test_opening_at_drop_time_is_a_release(self):
        assert is_release(dt.datetime(2026, 9, 23, 9, 3), self.venue, 5)

    def test_opening_away_from_drop_time_is_a_cancellation(self):
        assert not is_release(dt.datetime(2026, 9, 23, 9, 6), self.venue, 5)

    def test_window_wraps_midnight(self):
        venue = {"dropTimeDiscovery": {"actualDropTime": "23:59:00"}}
        assert is_release(dt.datetime(2026, 9, 23, 0, 2), venue, 5)

    def test_unknown_drop_time_counts_as_cancellation(self):
        assert not is_release(dt.datetime(2026, 9, 23, 9, 0), {}, 5)
        assert not is_release(dt.datetime(2026, 9, 23, 9, 0), None, 5)
