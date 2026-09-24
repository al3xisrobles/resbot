"""
Pure decision logic for cancellation watches: slot keys, snapshot diffs,
release classification and first-come slot assignment. No I/O here, so every
rule can be tested with plain data.
"""

import datetime as dt
from typing import Dict, Iterable, List, Optional

from .resy_client.models import Slot


def slot_key(slot: Slot) -> str:
    """Identity of a slot across polls: start time plus seating type, e.g. '19:30|Dining Room'."""
    return f"{slot.date.start.strftime('%H:%M')}|{slot.config.type}"


def slot_quantity(slot: Slot) -> int:
    """How many identical tables this slot stands for (Resy's `quantity`, default 1)."""
    try:
        return max(int((slot.model_extra or {}).get("quantity") or 1), 1)
    except (TypeError, ValueError):
        return 1


def slot_quantities(slots: Iterable[Slot]) -> Dict[str, int]:
    """Snapshot of a date: {slot key: number of tables}."""
    counts: Dict[str, int] = {}
    for slot in slots:
        key = slot_key(slot)
        counts[key] = counts.get(key, 0) + slot_quantity(slot)
    return counts


def new_openings(previous, current: Dict[str, int]) -> List[str]:
    """
    Slot keys that gained tables since the last poll: a new key, or more tables at a
    key already shown (someone cancelled at a time that still had a table left).

    A date seen for the first time (previous is None) is a baseline, not a burst of
    openings, so it reports nothing. So is a snapshot in the old list format, written
    before quantities were tracked. A date previously seen with no slots ({}) reports
    every current slot, because each of those did open since the last poll.
    """
    if previous is None or isinstance(previous, list):
        return []
    return sorted(k for k, n in current.items() if n > int(previous.get(k, 0)))


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")[:2]
    return int(hour) * 60 + int(minute)


def in_range(slot: Slot, range_start: str, range_end: str) -> bool:
    """True if the slot starts inside the watch's range, inclusive at both ends."""
    start = slot.date.start.hour * 60 + slot.date.start.minute
    return _minutes(range_start) <= start <= _minutes(range_end)


def matches_watch(slot: Slot, watch: dict) -> bool:
    seating = watch.get("seatingType")
    if seating not in (None, "", "any") and slot.config.type != seating:
        return False
    return in_range(slot, watch["rangeStart"], watch["rangeEnd"])


def _arrival_order(watch: dict):
    created = watch.get("createdAt")
    # Firestore returns timezone-aware datetimes; a watch not yet stamped sorts last.
    return (created.timestamp() if created else float("inf"), watch["jobId"])


def assign_slots(watches: List[dict], slots: List[Slot]) -> Dict[str, Slot]:
    """
    First come, first served: the oldest watch takes the earliest slot in its range
    that older watches have not used up (a slot with quantity N serves N watches).
    Returns {jobId: slot}. Watches left without a slot are simply absent.

    This is greedy, not a maximum matching, on purpose: a maximum matching can serve
    more watches in a burst but would sometimes hand an older watch's slot to a newer one.
    """
    ordered_slots = sorted(slots, key=lambda s: s.date.start)
    remaining = slot_quantities(slots)  # a slot with quantity 2 can serve two watches
    assignments: Dict[str, Slot] = {}
    for watch in sorted(watches, key=_arrival_order):
        for slot in ordered_slots:
            key = slot_key(slot)
            if remaining.get(key, 0) <= 0 or not matches_watch(slot, watch):
                continue
            remaining[key] -= 1
            assignments[watch["jobId"]] = slot
            break
    return assignments


def is_release(detected_at: dt.datetime, venue_doc: Optional[dict], window_minutes: int) -> bool:
    """
    True if an opening was detected within window_minutes of the venue's known drop time
    (time of day, from dropTimeDiscovery written by discovery-mode snipes). Without a
    known drop time we cannot tell, and count it as a cancellation.
    """
    drop = ((venue_doc or {}).get("dropTimeDiscovery") or {}).get("actualDropTime")
    if not drop:
        return False
    parts = [int(p) for p in drop.split(":")]
    drop_seconds = parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)
    detected_seconds = detected_at.hour * 3600 + detected_at.minute * 60 + detected_at.second
    diff = abs(detected_seconds - drop_seconds)
    diff = min(diff, 24 * 3600 - diff)  # a drop at 23:59 and a detection at 00:01 are 2 minutes apart
    return diff <= window_minutes * 60
