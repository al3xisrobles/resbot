"""
Claiming and booking for cancellation watches.

The tick assigns each opening to at most one watch (watch_match.assign_slots). This
module books exactly that slot with the watcher's own Resy account, and guarantees a
watch books at most once even when two ticks overlap: a watch must be claimed in a
Firestore transaction before its booking call goes out.
"""

import datetime as dt
import logging
import os
from typing import Optional

import requests
import sentry_sdk
from google.cloud import firestore as gc_firestore

from .constants import (
    WATCH_BOOKING_ENABLED_ENV,
    WATCH_CLAIM_STALE_SECONDS,
    WATCH_MAX_BOOKING_FAILURES,
)
from .resy_client.errors import (
    NoSlotsError,
    RateLimitError,
    ResyApiError,
    ResyAuthError,
    ResyTransientError,
    SlotTakenError,
)
from .resy_client.model_builders import build_find_request_body
from .snipe import _build_reservation_request_from_dict
from .watch_match import slot_key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Outcomes of one booking attempt
BOOKED = "booked"
GONE = "gone"            # the slot vanished or someone else got it: keep watching
TRANSIENT = "transient"  # Resy or network hiccup: keep watching, not counted
AUTH = "auth"            # session expired: end the watch, user must reconnect
FAILURE = "failure"      # anything else: counted toward WATCH_MAX_BOOKING_FAILURES

# Statuses Resy returns when the slot is no longer bookable
_GONE_STATUSES = frozenset({404, 409, 410, 412})

AUTH_EXPIRED_MESSAGE = "Resy session expired. Please reconnect your Resy account."


def booking_enabled() -> bool:
    """Booking stays off (shadow mode) unless the env flag is exactly 'true'."""
    return os.getenv(WATCH_BOOKING_ENABLED_ENV, "").strip().lower() == "true"


def claim_available(job: dict, now: dt.datetime) -> bool:
    """A watch can be claimed if it is still pending and has no live claim."""
    if job.get("status") != "pending":
        return False
    claimed_at = job.get("bookingClaimedAt")
    if claimed_at is None:
        return True
    # A tick that crashed mid-booking leaves a claim behind; don't let it block forever.
    return (now - claimed_at).total_seconds() > WATCH_CLAIM_STALE_SECONDS


def classify_error(error: Exception) -> str:
    if isinstance(error, ResyAuthError):
        return AUTH
    if isinstance(error, (NoSlotsError, SlotTakenError)):
        return GONE
    if isinstance(error, (RateLimitError, ResyTransientError, requests.exceptions.RequestException)):
        return TRANSIENT
    if isinstance(error, ResyApiError) and error.status_code in _GONE_STATUSES:
        return GONE
    return FAILURE


def _claim(db, job_id: str, now: dt.datetime) -> Optional[dict]:
    """Atomically claim a watch. Returns the job data if this caller won the claim."""
    job_ref = db.collection("reservationJobs").document(job_id)

    @gc_firestore.transactional
    def _txn(transaction):
        snap = job_ref.get(transaction=transaction)
        if not snap.exists:
            return None
        job = snap.to_dict()
        if not claim_available(job, now):
            return None
        transaction.update(job_ref, {"bookingClaimedAt": now})
        return job

    return _txn(db.transaction())


def book_assigned_slot(job: dict, assigned_key: str) -> str:
    """
    Book the slot the tick assigned to this watch, using the watcher's own token.

    Re-finds with the user's token rather than booking our unauthenticated poll's slot,
    and books only the slot with the assigned key. Letting the selector pick instead
    could make two watchers race for the same slot.
    """
    reservation_request, manager = _build_reservation_request_from_dict(job, job.get("userId"))
    slots = manager.api_access.find_booking_slots(build_find_request_body(reservation_request))
    slot = next((s for s in slots if slot_key(s) == assigned_key), None)
    if slot is None:
        raise NoSlotsError(f"Assigned slot {assigned_key} is no longer available")
    return manager._try_book_slot(slot, reservation_request)  # pylint: disable=protected-access


def attempt_booking(db, job_id: str, assigned_key: str, now: dt.datetime) -> Optional[str]:
    """
    Claim the watch, book its assigned slot, and record the result on the job doc.
    Returns the outcome, or None if another tick holds the claim.
    """
    job = _claim(db, job_id, now)
    if job is None:
        return None

    job_ref = db.collection("reservationJobs").document(job_id)
    log_entry = {"timestamp": now.isoformat(), "slot": assigned_key}
    try:
        resy_token = book_assigned_slot(job, assigned_key)
    except Exception as e:  # pylint: disable=broad-exception-caught
        outcome = classify_error(e)
        _record_failure(job_ref, job, outcome, str(e), log_entry)
        if outcome == FAILURE:
            sentry_sdk.capture_exception(e)
        logger.warning("[watch_booking] Job %s booking %s: %s (%s)", job_id, assigned_key, outcome, e)
        return outcome

    job_ref.update({
        "status": "done",
        "resyToken": resy_token,
        "errorMessage": None,
        "bookingClaimedAt": None,
        "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
        "executionLogs": gc_firestore.ArrayUnion([{**log_entry, "status": "success",
                                                   "message": "Booked a cancellation"}]),
    })
    logger.info("[watch_booking] Job %s booked %s", job_id, assigned_key)
    return BOOKED


def _record_failure(job_ref, job: dict, outcome: str, message: str, log_entry: dict) -> None:
    update = {
        "bookingClaimedAt": None,
        "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
        "executionLogs": gc_firestore.ArrayUnion([{**log_entry, "status": outcome, "message": message}]),
    }
    if outcome == AUTH:
        update.update({"status": "failed", "errorMessage": AUTH_EXPIRED_MESSAGE})
    elif outcome == FAILURE:
        failures = int(job.get("bookingFailures", 0)) + 1
        update["bookingFailures"] = failures
        if failures >= WATCH_MAX_BOOKING_FAILURES:
            update.update({"status": "failed", "errorMessage": message})
    job_ref.update(update)
