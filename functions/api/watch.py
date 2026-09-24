"""
Cancellation watch tick.

One shared poller serves every watch. Each tick:
  1. queues the next tick for exactly 60 seconds after its own scheduled time,
  2. loads pending watches and groups them into targets (venueId, partySize),
  3. polls /4/venue/calendar once per target, and /4/find for watched dates that
     are available, without any user token,
  4. diffs slots against the last snapshot and logs each opening to watchEvents,
  5. assigns slots to watches first come, first served, and books them when
     booking is enabled (otherwise the assignment is only logged: shadow mode).

The chain runs on Cloud Tasks because Cloud Scheduler cannot fire at a chosen second.
seed_watch_tick is a watchdog that restarts the chain if it ever breaks. Both share a
deterministic task ID per minute, so the chain can never fork. See
specs/cancellation-watch/SPEC.md for the reasoning and the cost model.
"""

import datetime as dt
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import firebase_admin
import google.auth.transport.requests
import sentry_sdk
from firebase_admin import exceptions as fb_exceptions
from firebase_admin import firestore
from firebase_admin import functions as fb_functions
from firebase_functions import scheduler_fn, tasks_fn
from firebase_functions.options import MemoryOption, RateLimits, RetryConfig
from google.cloud import firestore as gc_firestore
from sentry_sdk.crons import monitor

from .constants import (
    WATCH_MAX_TARGETS,
    WATCH_POLL_WORKERS,
    WATCH_QUIET_END_HOUR,
    WATCH_QUIET_START_HOUR,
    WATCH_QUIET_TIMEZONE,
    WATCH_RELEASE_WINDOW_MINUTES,
    WATCH_TARGET_BACKOFF_SECONDS,
    WATCH_TICK_SECOND,
    WATCH_TICK_TIMEOUT_SECONDS,
)
from .resy_client.api_access import ResyApiAccess, build_resy_client
from .resy_client.errors import RateLimitError
from .resy_client.models import CalendarRequestParams, FindRequestBody, ResyConfig
from .watch_booking import BOOKED, attempt_booking, booking_enabled
from .watch_limits import load_active_watches, target_id
from .watch_match import assign_slots, is_release, new_slot_keys, slot_key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Firebase names a task function's Cloud Tasks queue after the function, and queue IDs
# allow only letters, digits and hyphens. An underscore in the name fails the deploy.
TICK_FUNCTION_NAME = "watchtick"
# A Retry-After longer than this backs the target off instead of sleeping inside the tick.
POLL_MAX_RETRY_DELAY_SECONDS = 2.0
DEFAULT_RESY_API_KEY = "VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"  # the public web app key, same as utils.py

_db = None


def get_db():
    """Lazily get Firestore client so we don't require ADC at import time."""
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


# --- Scheduling ---------------------------------------------------------------


def in_quiet_hours(moment: dt.datetime) -> bool:
    local = moment.astimezone(ZoneInfo(WATCH_QUIET_TIMEZONE))
    return WATCH_QUIET_START_HOUR <= local.hour < WATCH_QUIET_END_HOUR


def next_seed_time(now: dt.datetime) -> dt.datetime:
    """The next second WATCH_TICK_SECOND at least a couple of seconds from now."""
    candidate = now.replace(second=WATCH_TICK_SECOND, microsecond=0)
    if candidate <= now + dt.timedelta(seconds=2):
        candidate += dt.timedelta(minutes=1)
    return candidate


def tick_task_id(scheduled_for: dt.datetime) -> str:
    return f"watch-tick-{scheduled_for.astimezone(dt.timezone.utc):%Y%m%d%H%M}"


def _ensure_credential_email() -> None:
    """
    firebase-admin builds the task's OIDC token from the credential's service account
    email before its own request refreshes the credential. On Cloud Run that email reads
    "default" until the first refresh, and Cloud Tasks rejects "default" with a 400
    (invalid argument). Refreshing once per instance resolves the real email.
    """
    credential = firebase_admin.get_app().credential.get_credential()
    if getattr(credential, "service_account_email", None) == "default":
        credential.refresh(google.auth.transport.requests.Request())


def enqueue_tick(scheduled_for: dt.datetime) -> bool:
    """
    Queue a tick. Returns False if a tick for that minute already exists, which is
    the normal case when the watchdog runs while the chain is alive.
    """
    _ensure_credential_email()
    options = fb_functions.TaskOptions(
        schedule_time=scheduled_for,
        task_id=tick_task_id(scheduled_for),
    )
    try:
        # The tasks handler only accepts a body of exactly {"data": ...}, the callable
        # protocol, but the Python Admin SDK sends the payload as given, so wrap it here.
        fb_functions.task_queue(TICK_FUNCTION_NAME).enqueue(
            {"data": {"scheduledFor": scheduled_for.isoformat()}}, options
        )
        return True
    except fb_exceptions.AlreadyExistsError:
        return False


@scheduler_fn.on_schedule(
    schedule="every 5 minutes",
    timeout_sec=30,
    memory=MemoryOption.MB_256,
)
@monitor(monitor_slug="watch-tick-seed", monitor_config={
    "schedule": {"type": "interval", "value": 5, "unit": "minute"},
    "checkin_margin": 5,
    "max_runtime": 1,
    "failure_issue_threshold": 2,
})
def seed_watch_tick(_event: scheduler_fn.ScheduledEvent) -> None:
    """Watchdog: restart the tick chain if it broke. A no-op while the chain is alive."""
    now = dt.datetime.now(dt.timezone.utc)
    if in_quiet_hours(now):
        return
    scheduled_for = next_seed_time(now)
    if enqueue_tick(scheduled_for):
        logger.warning("[seed_watch_tick] Tick chain was not running; seeded %s", scheduled_for.isoformat())


@tasks_fn.on_task_dispatched(
    retry_config=RetryConfig(max_attempts=1),  # a missed tick is replaced by the next one, never retried
    rate_limits=RateLimits(max_concurrent_dispatches=1),
    timeout_sec=WATCH_TICK_TIMEOUT_SECONDS,
    memory=MemoryOption.MB_256,
    max_instances=1,
)
def watchtick(req: tasks_fn.CallableRequest) -> None:
    started = dt.datetime.now(dt.timezone.utc)
    process_tick(_parse_scheduled_for((req.data or {}).get("scheduledFor"), started), started)


def process_tick(scheduled_for: dt.datetime, started: dt.datetime, db=None) -> Optional[dict]:
    """One tick: queue the successor, then poll. Returns the tick's stats, or None if skipped."""
    # Queue the successor first, from our own scheduled time rather than the clock, so a
    # crash mid-poll does not break the chain and a late start never skips a minute.
    successor = scheduled_for + dt.timedelta(minutes=1)
    if not in_quiet_hours(successor):
        try:
            enqueue_tick(successor)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # The watchdog restarts the chain within 5 minutes; keep this tick's poll.
            logger.error("[watchtick] Failed to enqueue successor: %s", e)
            sentry_sdk.capture_exception(e)

    if in_quiet_hours(started):
        return None

    try:
        stats = run_tick(db or get_db(), started)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("[watchtick] Tick failed: %s", e)
        sentry_sdk.capture_exception(e)
        return None

    logger.info(
        "[watchtick] scheduled=%s start_lag_s=%.2f first_poll_second=%s duration_s=%.2f "
        "watches=%d targets=%d calendar_calls=%d find_calls=%d openings=%d assignments=%d "
        "bookings=%d rate_limited=%d errors=%d skipped_backoff=%d",
        scheduled_for.isoformat(),
        (started - scheduled_for).total_seconds(),
        stats.get("first_poll_second"),
        (dt.datetime.now(dt.timezone.utc) - started).total_seconds(),
        stats["watches"], stats["targets"], stats["calendar_calls"], stats["find_calls"],
        stats["openings"], stats["assignments"], stats["bookings"], stats["rate_limited"],
        stats["errors"], stats["skipped_backoff"],
    )
    return stats


def _parse_scheduled_for(value: Optional[str], fallback: dt.datetime) -> dt.datetime:
    if not value:
        return fallback.replace(second=WATCH_TICK_SECOND, microsecond=0)
    parsed = dt.datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


# --- The tick -------------------------------------------------------------------


def build_poll_client() -> ResyApiAccess:
    """
    A Resy client with the public API key and no auth token. Never use load_credentials
    here: without a userId it falls back to RESY_TOKEN, which may be the owner's account,
    and polling on a real account is what gets accounts banned.
    """
    api_key = os.getenv("RESY_API_KEY", DEFAULT_RESY_API_KEY)
    access = build_resy_client(ResyConfig(api_key=api_key, token=""))
    access.client.max_retry_delay = POLL_MAX_RETRY_DELAY_SECONDS
    return access


def watch_end_time(watch: dict) -> dt.datetime:
    tz = ZoneInfo(watch.get("timezone") or "America/New_York")
    day = dt.date.fromisoformat(watch["date"])
    hour, minute = (int(p) for p in watch["rangeEnd"].split(":")[:2])
    return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)


def expire_watches(db, watches: List[dict], now: dt.datetime) -> List[dict]:
    """End watches whose latest acceptable time has passed. Returns the ones still live."""
    live = []
    for watch in watches:
        if watch_end_time(watch) > now:
            live.append(watch)
            continue
        db.collection("reservationJobs").document(watch["jobId"]).update({
            "status": "failed",
            "errorMessage": "Watch ended without an opening in your time range.",
            "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
        })
    return live


def group_by_target(watches: List[dict]) -> Dict[str, List[dict]]:
    targets: Dict[str, List[dict]] = {}
    for watch in watches:
        targets.setdefault(target_id(watch["venueId"], watch["partySize"]), []).append(watch)
    return targets


def run_tick(db, now: dt.datetime, client: Optional[ResyApiAccess] = None) -> dict:
    stats = {
        "watches": 0, "targets": 0, "calendar_calls": 0, "find_calls": 0, "openings": 0,
        "assignments": 0, "bookings": 0, "rate_limited": 0, "errors": 0, "skipped_backoff": 0,
        "first_poll_second": None,
    }
    watches = expire_watches(db, load_active_watches(db), now)
    targets = group_by_target(watches)
    stats["watches"] = len(watches)
    stats["targets"] = len(targets)
    if not targets:
        return stats
    if len(targets) > WATCH_MAX_TARGETS:
        # create_snipe enforces the cap; more targets than that means the cap was bypassed.
        logger.warning("[run_tick] %d targets exceed the cap of %d", len(targets), WATCH_MAX_TARGETS)

    client = client or build_poll_client()
    moment = dt.datetime.now(dt.timezone.utc)
    # When polls start, to check the WATCH_TICK_SECOND offset survives cold starts.
    stats["first_poll_second"] = round(moment.second + moment.microsecond / 1e6, 2)
    with ThreadPoolExecutor(max_workers=WATCH_POLL_WORKERS) as pool:
        results = list(pool.map(
            lambda item: poll_target(db, client, item[0], item[1], now), targets.items()
        ))
    for result in results:
        for key, value in result.items():
            stats[key] += value
    return stats


def poll_target(db, client: ResyApiAccess, target: str, watches: List[dict], now: dt.datetime) -> dict:
    """Poll one target, record openings, and book assignments. Never raises."""
    stats = {"calendar_calls": 0, "find_calls": 0, "openings": 0, "assignments": 0,
             "bookings": 0, "rate_limited": 0, "errors": 0, "skipped_backoff": 0}
    target_ref = db.collection("watchTargets").document(target)
    snap = target_ref.get()
    state = snap.to_dict() if snap.exists else {}

    backoff_until = state.get("backoffUntil")
    if backoff_until and backoff_until > now:
        stats["skipped_backoff"] = 1
        return stats

    venue_id = watches[0]["venueId"]
    party_size = int(watches[0]["partySize"])
    dates = sorted({w["date"] for w in watches})
    previous_slots: Dict[str, List[str]] = state.get("slots") or {}

    try:
        stats["calendar_calls"] += 1
        calendar = client.get_calendar(CalendarRequestParams(
            venue_id=str(venue_id), num_seats=party_size, start_date=dates[0], end_date=dates[-1],
        ))
        statuses = {
            entry.date: (entry.inventory.reservation if entry.inventory else None)
            for entry in calendar.scheduled if entry.date in dates
        }

        current_slots: Dict[str, List[str]] = {}
        openings: List[dict] = []
        for day in dates:
            if statuses.get(day) != "available":
                current_slots[day] = []
                continue
            stats["find_calls"] += 1
            day_watches = [w for w in watches if w["date"] == day]
            current_slots[day], day_openings = _poll_date(
                db, client, venue_id, party_size, day, day_watches, previous_slots.get(day), now, stats
            )
            openings.extend(day_openings)

        stats["openings"] = len(openings)
        if openings:
            _record_openings(db, target, watches[0], openings, now)

        update = {"calendar": statuses, "slots": current_slots, "backoffUntil": None}
        if update["calendar"] != state.get("calendar") or current_slots != previous_slots \
                or state.get("backoffUntil") is not None:
            target_ref.set({**update, "lastChangedAt": now}, merge=True)
    except RateLimitError as e:
        stats["rate_limited"] = 1
        wait = max(WATCH_TARGET_BACKOFF_SECONDS, int(e.retry_after or 0))
        target_ref.set({"backoffUntil": now + dt.timedelta(seconds=wait)}, merge=True)
        logger.warning("[poll_target] %s rate limited; backing off %ss", target, wait)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # One target's failure must never stop the others.
        stats["errors"] = 1
        logger.error("[poll_target] %s failed: %s", target, e)
        sentry_sdk.capture_exception(e)
    return stats


def _poll_date(db, client: ResyApiAccess, venue_id, party_size: int, day: str, watches: List[dict],
               previous: Optional[List[str]], now: dt.datetime, stats: dict) -> tuple[List[str], List[dict]]:
    """Find slots for one available date, assign them, and book or log the assignments."""
    venue = client.find_venue_result(FindRequestBody(venue_id=int(venue_id), party_size=party_size, day=day))
    slots = venue.slots if venue else []
    keys = sorted({slot_key(s) for s in slots})
    assignments = assign_slots(watches, slots)
    assigned_by_key = {slot_key(s): job_id for job_id, s in assignments.items()}
    stats["assignments"] += len(assignments)

    openings = [
        {"date": day, "slotKey": key, "assignedJobId": assigned_by_key.get(key)}
        for key in new_slot_keys(previous, keys)
    ]

    if booking_enabled():
        for job_id, slot in assignments.items():
            if attempt_booking(db, job_id, slot_key(slot), now) == BOOKED:
                stats["bookings"] += 1
    elif assignments:
        logger.info("[poll_target] Shadow mode: would book %s", assigned_by_key)
    return keys, openings


def _record_openings(db, target: str, watch: dict, openings: List[dict], now: dt.datetime) -> None:
    venue_id = str(watch["venueId"])
    venue_snap = db.collection("venues").document(venue_id).get()
    venue_doc = venue_snap.to_dict() if venue_snap.exists else None
    # Drop times are recorded in the venue's local time, which is the watch's timezone.
    local_now = now.astimezone(ZoneInfo(watch.get("timezone") or "America/New_York"))
    release = is_release(local_now, venue_doc, WATCH_RELEASE_WINDOW_MINUTES)
    batch = db.batch()
    for opening in openings:
        batch.set(db.collection("watchEvents").document(), {
            "target": target,
            "venueId": venue_id,
            "partySize": int(watch["partySize"]),
            **opening,
            "detectedAt": now,
            "isRelease": release,
            "bookingEnabled": booking_enabled(),
        })
    batch.commit()
    logger.info("[poll_target] %s: %d openings %s", target, len(openings), [o["slotKey"] for o in openings])
