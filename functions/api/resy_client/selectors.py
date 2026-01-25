import logging
from datetime import datetime, timedelta
from typing import List
from abc import ABC, abstractmethod
from bisect import bisect_left

from .errors import NoSlotsError
from .models import Slot, ReservationRequest

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class AbstractSelector(ABC):
    @abstractmethod
    def select(self, slots: List[Slot], request: ReservationRequest) -> Slot:
        pass

    def select_top_n(self, slots: List[Slot], request: ReservationRequest, n: int = 3) -> List[Slot]:  # pylint: disable=unused-argument
        """Return the top N candidates, ordered by preference. Default impl returns single best."""
        # Note: n is intentionally unused in base implementation - subclasses should override
        return [self.select(slots, request)]

class SimpleSelector:
    def select(self, slots, request):
        ideal = datetime(
            request.target_date.year,
            request.target_date.month,
            request.target_date.day,
            request.ideal_hour,
            request.ideal_minute,
        )
        window = timedelta(hours=request.window_hours)
        min_time = ideal - window
        max_time = ideal + window

        # Slots already sorted by start time
        times = [s.date.start for s in slots]

        # Find the insertion point for the ideal time
        mid = bisect_left(times, ideal)

        best_slot = None
        best_diff = None

        def ok(s):
            """Check if slot matches preferred dining type if specified."""
            if request.preferred_type is not None and s.config.type != request.preferred_type:
                return False
            return True

        # Pointers for left and right expansion
        left = mid - 1
        right = mid

        # Expand outwards from the ideal time
        while left >= 0 or right < len(slots):
            # Pick the closer side to check next
            left_diff = abs(times[left] - ideal) if left >= 0 else None
            right_diff = abs(times[right] - ideal) if right < len(slots) else None

            # If we already have a best, and the next closest candidate is worse, we can stop
            next_diff = min(d for d in [left_diff, right_diff] if d is not None)
            if best_diff is not None and next_diff > best_diff:
                break

            # Check right if it's closer (or tie — tie-handling happens below)
            if right_diff is not None and (left_diff is None or right_diff <= left_diff):
                t = times[right]
                s = slots[right]
                right += 1
            else:
                # Check left
                t = times[left]
                s = slots[left]
                left -= 1

            if t < min_time or t > max_time:
                continue
            if not ok(s):
                continue

            # If we found a perfect match, return it immediately (short circuit)
            diff = abs(t - ideal)
            if diff == timedelta(0):
                return s

            if best_slot is None:
                best_slot, best_diff = s, diff
                continue

            if diff < best_diff:
                best_slot, best_diff = s, diff
            elif diff == best_diff:
                # tie-break: earlier vs later
                if request.prefer_early:
                    if t < best_slot.date.start:
                        best_slot = s
                else:
                    if t > best_slot.date.start:
                        best_slot = s

        if best_slot is None:
            raise NoSlotsError("No acceptable slots found")
        return best_slot

    def select_top_n(self, slots: List[Slot], request: ReservationRequest, n: int = 3) -> List[Slot]:
        """
        Return the top N slots ordered by preference (closest to ideal time first).
        Useful for parallel booking attempts.
        """
        ideal = datetime(
            request.target_date.year,
            request.target_date.month,
            request.target_date.day,
            request.ideal_hour,
            request.ideal_minute,
        )
        window = timedelta(hours=request.window_hours)
        min_time = ideal - window
        max_time = ideal + window

        def ok(s):
            if request.preferred_type is not None and s.config.type != request.preferred_type:
                return False
            return True

        # Filter to acceptable slots within window
        candidates = [
            s for s in slots
            if min_time <= s.date.start <= max_time and ok(s)
        ]

        if not candidates:
            raise NoSlotsError("No acceptable slots found")

        # Sort by distance from ideal, then by preference (early vs late)
        def sort_key(s):
            diff = abs(s.date.start - ideal)
            # Tie-breaker: prefer earlier or later based on request
            tie_breaker = s.date.start if request.prefer_early else -s.date.start.timestamp()
            return (diff, tie_breaker)

        candidates.sort(key=sort_key)
        return candidates[:n]
