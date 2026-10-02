"""
Backoff from Resy's bot block, and the search for how long it takes to clear.

Resy's bot protection answers 500 once it trips, and it blocks the poller as a whole,
not one restaurant. A block is an episode with one state, shared by every target:

  1. The first 500 opens the episode. Probes go out 1, 2, 4, 8, 16... minutes apart,
     doubling until they reach the episode's ceiling, then repeat at the ceiling.
  2. A probe that gets through closes the episode as a pass for its ceiling, and polling
     goes back to every minute.
  3. A ceiling that has probed for WATCH_BLOCK_CEILING_TRIAL_HOURS without a pass fails.
     The ceiling then moves up and the episode carries on under the new one.
  4. Quiet hours cut an open episode short; it counts as neither pass nor fail.

Ceilings move through `lo` (highest ceiling that failed) and `hi` (lowest that passed).
Until something passes, the ceiling climbs from 20 minutes in 10-minute steps up to 60.
Once there is a pass, each new episode tries the midpoint of lo and hi, and the search
stops when they are WATCH_BLOCK_SEARCH_PRECISION_MINUTES apart; from then on, hi is used.

These functions are pure: they take the state dict stored in Firestore and the time,
and return the new state. watch.run_tick loads and saves it.
"""
import datetime as dt
from typing import List, Optional
from zoneinfo import ZoneInfo

from .constants import (
    WATCH_BLOCK_CEILING_STEP_MINUTES,
    WATCH_BLOCK_CEILING_TRIAL_HOURS,
    WATCH_BLOCK_MAX_CEILING_MINUTES,
    WATCH_BLOCK_SEARCH_PRECISION_MINUTES,
    WATCH_BLOCK_START_CEILING_MINUTES,
    WATCH_QUIET_START_HOUR,
    WATCH_QUIET_TIMEZONE,
)

# Ticks start a fraction of a second either side of :50, so a probe due at 12:10:50.2
# must still go out on the 12:10:50.1 tick rather than wait a whole extra minute.
PROBE_SLACK = dt.timedelta(seconds=30)
HISTORY_LIMIT = 200  # episodes kept on the state doc for analysis

PASS = "pass"
FAIL = "fail"
CENSORED = "censored"


def initial_state() -> dict:
    return {"blockedSince": None, "lo": None, "hi": None, "history": []}


def is_blocked(state: dict) -> bool:
    return state.get("blockedSince") is not None


def search_done(state: dict) -> bool:
    lo, hi = state.get("lo"), state.get("hi")
    return hi is not None and (hi - (lo or 0)) <= WATCH_BLOCK_SEARCH_PRECISION_MINUTES


def choose_ceiling(lo: Optional[int], hi: Optional[int]) -> int:
    """The ceiling the next episode, or the next trial within one, should use."""
    if hi is None:
        if lo is None:
            return WATCH_BLOCK_START_CEILING_MINUTES
        return min(lo + WATCH_BLOCK_CEILING_STEP_MINUTES, WATCH_BLOCK_MAX_CEILING_MINUTES)
    low = lo or 0
    if hi - low <= WATCH_BLOCK_SEARCH_PRECISION_MINUTES:
        return hi
    return (low + hi) // 2


def should_probe(state: dict, now: dt.datetime) -> bool:
    """While blocked, whether this tick sends a probe. Outside a block, every tick polls."""
    if not is_blocked(state):
        return True
    return now + PROBE_SLACK >= state["nextProbeAt"]


def on_block(state: dict, now: dt.datetime) -> dict:
    """A poll got a 500 outside a block: open an episode."""
    ceiling = choose_ceiling(state.get("lo"), state.get("hi"))
    return {
        **state,
        "blockedSince": now,
        "ceiling": ceiling,
        "ceilingSince": now,
        "probeDelay": 1,
        "nextProbeAt": now + dt.timedelta(minutes=1),
        "probes": 0,
    }


def on_probe_failed(state: dict, now: dt.datetime) -> tuple[dict, List[str]]:
    """
    A probe got another 500. Doubles the wait up to the ceiling, and fails the ceiling
    once it has run for the trial period. Returns the new state and notes to log.
    """
    notes = []
    state = {**state, "probes": state.get("probes", 0) + 1}
    ceiling = state["ceiling"]
    delay = min(state["probeDelay"] * 2, ceiling)

    if now - state["ceilingSince"] >= dt.timedelta(hours=WATCH_BLOCK_CEILING_TRIAL_HOURS):
        state = _record(state, now, FAIL)
        lo, hi = ceiling, state.get("hi")
        if hi is not None and hi <= lo:
            # The ceiling that once cleared a block did not clear this one. Results this
            # noisy cannot bracket anything, so forget the pass and climb from here.
            notes.append(f"ceiling {hi} passed before but failed now; dropping it")
            hi = None
        next_ceiling = choose_ceiling(lo, hi)
        if next_ceiling == ceiling:
            notes.append(f"ceiling {ceiling} failed and it is already the maximum")
        else:
            notes.append(f"ceiling {ceiling} failed after {WATCH_BLOCK_CEILING_TRIAL_HOURS}h; trying {next_ceiling}")
        state.update({"lo": lo, "hi": hi, "ceiling": next_ceiling, "ceilingSince": now})
        delay = next_ceiling

    state.update({"probeDelay": delay, "nextProbeAt": now + dt.timedelta(minutes=delay)})
    return state, notes


def on_probe_passed(state: dict, now: dt.datetime) -> tuple[dict, List[str]]:
    """A probe got through: close the episode as a pass for its ceiling."""
    ceiling = state["ceiling"]
    minutes = int((now - state["blockedSince"]).total_seconds() // 60)
    state = _record(state, now, PASS)
    lo, hi = state.get("lo"), ceiling
    notes = [f"block cleared after {minutes} min under ceiling {ceiling}"]
    if lo is not None and lo >= hi:
        notes.append(f"ceiling {lo} failed before but {hi} passed now; dropping the fail")
        lo = None
    state.update({"lo": lo, "hi": hi})
    if search_done(state):
        notes.append(f"search done: ceiling {hi}")
    return _cleared(state), notes


def censor_if_cut_by_quiet_hours(state: dict, now: dt.datetime) -> tuple[dict, bool]:
    """
    Quiet hours stop all probes, so an episode open across them has no outcome. Drop it
    and start the day polling normally. Returns the new state and whether it was cut.
    """
    if not is_blocked(state) or not _quiet_hours_started_between(state["blockedSince"], now):
        return state, False
    return _cleared(_record(state, now, CENSORED)), True


def _quiet_hours_started_between(start: dt.datetime, end: dt.datetime) -> bool:
    tz = ZoneInfo(WATCH_QUIET_TIMEZONE)
    local_end = end.astimezone(tz)
    last_start = local_end.replace(hour=WATCH_QUIET_START_HOUR, minute=0, second=0, microsecond=0)
    if last_start > local_end:
        last_start -= dt.timedelta(days=1)
    return start < last_start <= end


def _record(state: dict, now: dt.datetime, outcome: str) -> dict:
    entry = {
        "ceiling": state["ceiling"],
        "outcome": outcome,
        "trialStart": state["ceilingSince"],
        "blockedSince": state["blockedSince"],
        "end": now,
        "probes": state.get("probes", 0),
    }
    history = (list(state.get("history") or []) + [entry])[-HISTORY_LIMIT:]
    return {**state, "history": history}


def _cleared(state: dict) -> dict:
    return {
        **state,
        "blockedSince": None,
        "ceiling": None,
        "ceilingSince": None,
        "probeDelay": None,
        "nextProbeAt": None,
        "probes": 0,
    }
