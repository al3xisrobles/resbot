"""
Sniper Cloud Function for Resy Bot
Handles the actual reservation sniping at precise drop times
"""

import time
import datetime as dt
import logging
from typing import Optional

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption
from firebase_admin import firestore
from google.cloud import firestore as gc_firestore

from .sentry_utils import with_sentry_trace
from .resy_client.models import ResyConfig, ReservationRequest
from .resy_client.manager import ResyManager
from .resy_client.model_builders import build_find_request_body
from .resy_client.errors import RateLimitError, ResyAuthError
from .constants import (
    GEMINI_MODEL,
    DISCOVERY_WINDOW_BEFORE_MINUTES,
    DISCOVERY_WINDOW_AFTER_MINUTES,
    DISCOVERY_POLL_EARLY_SECONDS,
    DISCOVERY_POLL_ACTIVE_SECONDS,
    DISCOVERY_POLL_LATE_SECONDS,
    DISCOVERY_OBSERVATIONS_CAP,
    DISCOVERY_RATE_LIMIT_BACKOFF_MULTIPLIER,
)
from .utils import load_credentials, gemini_client
from .response_schemas import (
    success_response,
    error_response,
    SummaryData,
    SnipeResultData,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_db = None  # private global


def get_db():
    """Lazily get Firestore client so we don't require ADC at import time."""
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


def _build_reservation_request_from_dict(data: dict, user_id: str = None) -> tuple[ReservationRequest, ResyManager]:
    """
    Convert our stored job/reservation data dict into a ReservationRequest
    and a configured ResyManager.
    """
    # Load credentials (from Firestore if userId provided, else from credentials.json)
    credentials = load_credentials(user_id)
    # Explicitly set retry_on_taken_slot to True for now
    config = ResyConfig(**credentials, retry_on_taken_slot=True)

    reservation_data = {
        "party_size": int(data["partySize"]),
        "venue_id": data["venueId"],
        "window_hours": int(data.get("windowHours", 1)),
        "prefer_early": False,
        "ideal_date": data["date"],
        "ideal_hour": int(data["hour"]),
        "ideal_minute": int(data["minute"]),
        "preferred_type": (
            data.get("seatingType")
            if data.get("seatingType") not in (None, "", "any")
            else None
        ),
    }

    reservation_request = ReservationRequest(**reservation_data)
    manager = ResyManager.build(config)
    return reservation_request, manager


def _get_adaptive_interval(now: dt.datetime, expected_drop_time: dt.datetime) -> int:
    """
    Return poll interval in seconds based on time relative to expected drop.
    Early watch: >10 min before -> 60s; Active: -10 to +5 min -> 15s; Late: +5 to +30 min -> 30s.
    """
    minutes_until_drop = (expected_drop_time - now).total_seconds() / 60
    if minutes_until_drop > 10:
        return DISCOVERY_POLL_EARLY_SECONDS
    if minutes_until_drop > -5:
        return DISCOVERY_POLL_ACTIVE_SECONDS
    return DISCOVERY_POLL_LATE_SECONDS


def _check_slots_for_job(job_data: dict, user_id: str = None) -> tuple[int, Optional[Exception]]:
    """
    Call Resy /4/find for the job's venue/date/party_size. Returns (slot_count, error).
    """
    try:
        reservation_request, manager = _build_reservation_request_from_dict(job_data, user_id)
        find_body = build_find_request_body(reservation_request)
        slots = manager.api_access.find_booking_slots(find_body)
        return (len(slots), None)
    except Exception as e:
        return (0, e)


def _write_drop_time_to_venue(
    venue_id: str,
    job_id: str,
    expected_drop_time: dt.datetime,
    actual_drop_time: dt.datetime,
) -> None:
    """
    Merge dropTimeDiscovery onto venues/{venue_id}. Caps observations at DISCOVERY_OBSERVATIONS_CAP.
    """
    db = get_db()
    venue_ref = db.collection("venues").document(venue_id)
    venue_snap = venue_ref.get()
    existing = venue_snap.to_dict() if venue_snap.exists else {}
    discovery = existing.get("dropTimeDiscovery") or {}

    expected_str = expected_drop_time.strftime("%H:%M")
    actual_str = actual_drop_time.strftime("%H:%M:%S")
    actual_iso = actual_drop_time.isoformat()
    offset_minutes = (actual_drop_time - expected_drop_time).total_seconds() / 60
    new_obs = {
        "date": actual_drop_time.strftime("%Y-%m-%d"),
        "actualTime": actual_str,
        "offsetMinutes": round(offset_minutes, 2),
    }
    observations = list(discovery.get("observations", []))
    observations.append(new_obs)
    observations = observations[-DISCOVERY_OBSERVATIONS_CAP:]

    venue_ref.set(
        {
            "dropTimeDiscovery": {
                "expectedDropTime": expected_str,
                "actualDropTime": actual_str,
                "actualDropTimestamp": actual_iso,
                "offsetMinutes": round(offset_minutes, 2),
                "discoveredAt": gc_firestore.SERVER_TIMESTAMP,
                "discoveryJobId": job_id,
                "observationCount": len(observations),
                "observations": observations,
            }
        },
        merge=True,
    )
    logger.info(
        "[run_discovery_snipe] Wrote dropTimeDiscovery for venue %s (actual=%s)",
        venue_id,
        actual_iso,
    )


def _make_reservation_for_job(job_data: dict, user_id: str = None, use_parallel: bool = True) -> str:
    """
    Execute the reservation attempt using job_data stored in Firestore.
    Returns the resy_token (or raises on error).
    """
    logger.info("[snipe] Starting reservation for job %s at %s", job_data.get("jobId"), dt.datetime.now().isoformat())
    reservation_request, manager = _build_reservation_request_from_dict(job_data, user_id)
    if use_parallel:
        logger.info("[snipe] Using parallel booking strategy")
        return manager.make_reservation_parallel_with_retries(reservation_request, n_slots=3)
    return manager.make_reservation_with_retries(reservation_request)


def _load_job(req: Request) -> tuple[
    Optional[str], object, Optional[dict], Optional[str], Optional[dt.datetime], object
]:
    """
    Parse request body, load job from Firestore, validate targetTimeIso.
    Returns (job_id, job_ref, job_data, user_id, target_dt, error_response).
    error_response is None on success; if it is set, return it immediately.
    """
    body = req.get_json(silent=True) or {}
    job_id = body.get("jobId")
    if not job_id:
        return None, None, None, None, None, error_response("Missing jobId", 400)

    job_ref = get_db().collection("reservationJobs").document(job_id)
    snap = job_ref.get()
    if not snap.exists:
        return None, None, None, None, None, error_response("Job not found", 404)

    job_data = snap.to_dict()
    user_id = job_data.get("userId")
    target_iso = job_data.get("targetTimeIso")
    if not target_iso:
        return None, None, None, None, None, error_response("Job missing targetTimeIso", 400)

    return job_id, job_ref, job_data, user_id, dt.datetime.fromisoformat(target_iso), None


def _execute_booking_with_deadline(
    job_data: dict,
    user_id: Optional[str],
    execution_logs: list,
    deadline_seconds: int = 30,
) -> tuple[bool, Optional[str], Optional[str], bool]:
    """
    Attempt booking within a time deadline, handling rate limits and transient errors.
    Mutates execution_logs in place.
    Returns (success, resy_token, last_error, auth_expired).
    """
    success = False
    resy_token = None
    last_error = None
    rate_limit_count = 0
    start = time.time()

    while time.time() - start < deadline_seconds:
        try:
            resy_token = _make_reservation_for_job(job_data, user_id)
            success = True
            execution_logs.append({
                "timestamp": dt.datetime.now().isoformat(),
                "status": "success",
                "message": "Reservation successful",
            })
            break
        except ResyAuthError:
            last_error = "Resy session expired. Please reconnect your Resy account."
            return False, None, last_error, True
        except RateLimitError as rate_err:
            rate_limit_count += 1
            last_error = str(rate_err)
            elapsed = time.time() - start
            wait_time = min(2 * (2 ** (rate_limit_count - 1)), 8)
            execution_logs.append({
                "timestamp": dt.datetime.now().isoformat(),
                "status": "rate_limited",
                "message": f"Rate limited - waiting {wait_time:.1f}s",
                "elapsed_seconds": round(elapsed, 2),
            })
            if elapsed + wait_time < deadline_seconds:
                time.sleep(wait_time)
            else:
                break
        except Exception as inner_e:
            last_error = str(inner_e)
            elapsed = time.time() - start
            execution_logs.append({
                "timestamp": dt.datetime.now().isoformat(),
                "status": "error",
                "message": str(inner_e),
                "elapsed_seconds": round(elapsed, 2),
            })
            if elapsed < deadline_seconds:
                time.sleep(0.5)

    return success, resy_token, last_error, False


def _finalize_job(
    job_ref,
    job_id: str,
    success: bool,
    resy_token: Optional[str],
    last_error: Optional[str],
    execution_logs: list,
    extra_fields: Optional[dict] = None,
):
    """Persist final status to Firestore and return the HTTP response."""
    status = "done" if success else "failed"
    logger.info("[snipe] Job %s completed with status: %s", job_id, status)
    update = {
        "status": status,
        "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
        "resyToken": resy_token if success else None,
        "errorMessage": last_error if not success else None,
        "executionLogs": execution_logs,
    }
    if extra_fields:
        update.update(extra_fields)
    job_ref.update(update)
    return success_response(SnipeResultData(status=status, jobId=job_id, resyToken=resy_token))


def _handle_auth_expiry(job_ref, last_error: str, execution_logs: list):
    """Mark job failed due to session expiry and return HTTP 401."""
    job_ref.update({
        "status": "failed",
        "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
        "errorMessage": last_error,
        "executionLogs": execution_logs,
    })
    return error_response(last_error, 401)


def _handle_snipe_exception(req: Request, e: Exception, context: str):
    """Best-effort mark job as error in Firestore, then return HTTP 500."""
    try:
        body = req.get_json(silent=True) or {}
        job_id = body.get("jobId")
        if job_id:
            get_db().collection("reservationJobs").document(job_id).update({
                "status": "error",
                "errorMessage": str(e),
                "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
                "executionLogs": [{
                    "timestamp": dt.datetime.now().isoformat(),
                    "status": "error",
                    "message": f"{context}: {e}",
                }],
            })
    except Exception:
        pass
    return error_response(str(e), 500)


@on_request(
    cors=CorsOptions(
        cors_origins="*",
        cors_methods=["POST", "OPTIONS"],  # allow POST + OPTIONS
    ),
    timeout_sec=120,
    memory=MemoryOption.GB_1,
)
@with_sentry_trace
def run_snipe(req: Request):
    """
    Sniper function called by Cloud Scheduler.
    Body: { "jobId": "<firestore-doc-id>" }
    Sleeps until targetTimeIso then attempts booking for up to 30 seconds.
    """
    if req.method == "OPTIONS":
        return ("", 204)
    if req.method != "POST":
        return error_response("Method not allowed", 405)

    try:
        job_id, job_ref, job_data, user_id, target_dt, err = _load_job(req)
        if err is not None:
            return err

        now = dt.datetime.now(tz=target_dt.tzinfo)
        # Cloud Scheduler triggers ~1 min early; sleep until 0.1s before target
        delta_seconds = (target_dt - now).total_seconds() - 0.1
        logger.info("[run_snipe] Target: %s, sleeping %.2fs", target_dt.isoformat(), max(0, delta_seconds))
        if delta_seconds > 0:
            time.sleep(delta_seconds)

        execution_logs = []
        success, resy_token, last_error, auth_expired = _execute_booking_with_deadline(
            job_data, user_id, execution_logs
        )
        if auth_expired:
            return _handle_auth_expiry(job_ref, last_error, execution_logs)
        return _finalize_job(job_ref, job_id, success, resy_token, last_error, execution_logs)

    except Exception as e:
        return _handle_snipe_exception(req, e, "Exception during snipe execution")


@on_request(
    cors=CorsOptions(
        cors_origins="*",
        cors_methods=["POST", "OPTIONS"],
    ),
    timeout_sec=3600,
    memory=MemoryOption.MB_256,
)
@with_sentry_trace
def run_discovery_snipe(req: Request):
    """
    Discovery-mode snipe: poll /4/find in a time window around expected drop time,
    record the actual drop time on the venue doc when slots appear, then attempt booking.
    Called by Cloud Scheduler at (expected_drop - windowBeforeMinutes).

    Body: { "jobId": "<firestore-doc-id>" }
    """
    if req.method == "OPTIONS":
        return ("", 204)
    if req.method != "POST":
        return error_response("Method not allowed", 405)

    try:
        job_id, job_ref, job_data, user_id, target_dt, err = _load_job(req)
        if err is not None:
            return err

        if not job_data.get("discoveryMode"):
            return error_response("Job is not a discovery-mode job", 400)

        tz = target_dt.tzinfo
        now = dt.datetime.now(tz=tz)
        window_before = int(job_data.get("windowBeforeMinutes", DISCOVERY_WINDOW_BEFORE_MINUTES))
        window_after = int(job_data.get("windowAfterMinutes", DISCOVERY_WINDOW_AFTER_MINUTES))
        window_start = target_dt - dt.timedelta(minutes=window_before)
        window_end = target_dt + dt.timedelta(minutes=window_after)

        if now < window_start:
            sleep_sec = (window_start - now).total_seconds()
            logger.info("[run_discovery_snipe] Sleeping %.1fs until window start", sleep_sec)
            time.sleep(sleep_sec)
            now = dt.datetime.now(tz=tz)

        poll_log = []
        execution_logs = []
        current_interval = DISCOVERY_POLL_EARLY_SECONDS

        while now <= window_end:
            slot_count, poll_err = _check_slots_for_job(job_data, user_id)
            now = dt.datetime.now(tz=tz)
            poll_log.append({"t": now.strftime("%H:%M:%S"), "slots": slot_count})

            if poll_err:
                logger.warning("[run_discovery_snipe] Poll error: %s", poll_err)
                execution_logs.append({
                    "timestamp": now.isoformat(),
                    "status": "poll_error",
                    "message": str(poll_err),
                })
                if isinstance(poll_err, ResyAuthError):
                    return _handle_auth_expiry(
                        job_ref,
                        "Resy session expired during discovery. Please reconnect your Resy account and try again.",
                        execution_logs,
                    )
                if isinstance(poll_err, RateLimitError):
                    current_interval = min(
                        int(current_interval * DISCOVERY_RATE_LIMIT_BACKOFF_MULTIPLIER),
                        120,
                    )
                time.sleep(current_interval)
                continue

            if slot_count > 0:
                logger.info("[run_discovery_snipe] Slots detected (%d) at %s", slot_count, now.isoformat())
                _write_drop_time_to_venue(job_data["venueId"], job_id, target_dt, now)
                job_ref.update({
                    "discoveredDropTime": now.isoformat(),
                    "pollLog": poll_log,
                    "executionLogs": execution_logs,
                    "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
                })

                success, resy_token, last_error, auth_expired = _execute_booking_with_deadline(
                    job_data, user_id, execution_logs
                )
                if auth_expired:
                    return _handle_auth_expiry(job_ref, last_error, execution_logs)
                return _finalize_job(
                    job_ref, job_id, success, resy_token, last_error, execution_logs,
                    extra_fields={"pollLog": poll_log},
                )

            current_interval = _get_adaptive_interval(now, target_dt)
            time.sleep(current_interval)
            now = dt.datetime.now(tz=tz)

        logger.info("[run_discovery_snipe] Window expired without slots")
        job_ref.update({
            "status": "failed",
            "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
            "errorMessage": "Discovery window expired; no slots appeared",
            "pollLog": poll_log,
            "executionLogs": execution_logs,
        })
        return success_response(SnipeResultData(status="failed", jobId=job_id, resyToken=None))

    except Exception as e:
        return _handle_snipe_exception(req, e, "Exception during discovery")


@on_request(
    cors=CorsOptions(
        cors_origins="*",
        cors_methods=["POST", "OPTIONS"],
    ),
    timeout_sec=120,
    memory=MemoryOption.MB_512,
)
@with_sentry_trace
def summarize_snipe_logs(req: Request):
    """
    POST /summarize_snipe_logs
    Uses Gemini AI to summarize execution logs from a reservation attempt.
    Body: { "jobId": "<firestore-doc-id>" }

    Returns a 1-2 sentence summary of what happened during the reservation attempt.
    """
    # 1) Let preflight succeed without touching JSON
    if req.method == "OPTIONS":
        return ("", 204)

    # 2) Only process real POSTs
    if req.method != "POST":
        return error_response("Method not allowed", 405)

    try:
        if not gemini_client:
            return error_response(
                "Gemini API not configured. Please set GEMINI_API_KEY environment variable.",
                503
            )

        body = req.get_json(silent=True) or {}
        job_id = body.get("jobId")

        if not job_id:
            return error_response("Missing jobId", 400)

        # Load job from Firestore
        job_ref = get_db().collection("reservationJobs").document(job_id)
        snap = job_ref.get()

        if not snap.exists:
            return error_response("Job not found", 404)

        job_data = snap.to_dict()
        execution_logs = job_data.get("executionLogs", [])
        error_message = job_data.get("errorMessage")
        status = job_data.get("status", "unknown")

        # If no logs and no error message, return early
        if not execution_logs and not error_message:
            logger.info("[summarize_snipe_logs] No execution logs for job %s", job_id)
            return success_response(
                SummaryData(summary="No execution logs available for this reservation attempt.")
            )

        # Build prompt for Gemini
        logs_text = ""
        if execution_logs:
            logs_text = "Execution logs:\n"
            for log in execution_logs:
                timestamp = log.get("timestamp", "unknown")
                log_status = log.get("status", "unknown")
                message = log.get("message", "")
                elapsed = log.get("elapsed_seconds")
                if elapsed:
                    logs_text += f"- [{timestamp}] {log_status}: {message} (after {elapsed}s)\n"
                else:
                    logs_text += f"- [{timestamp}] {log_status}: {message}\n"

        if error_message:
            logs_text += f"\nFinal error message: {error_message}\n"

        prompt = f"""You are analyzing logs from an automated restaurant reservation attempt.

The reservation attempt had a final status of: {status}

{logs_text}

Provide a concise 1-2 sentence summary explaining what happened during this reservation attempt. Focus on why it might have failed. Be clear and user-friendly. Do not mention technical details like "execution logs" or "retry attempts" - just explain what happened in plain language.

GOOD EXAMPLES:
"The booking was unsuccessful due to rate limiting causing delays."
"No slots were available for the requested time."
"BUG: The /find endpoint returned a 500 server error. Maybe the request was malformed?"

BAD EXAMPLES:
"Retried 30 times with parallel booking, without securing a slot"
"The booking was unsuccessful"

If the status is "done", simply state that the reservation was successful."""

        # Call Gemini
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"temperature": 0.3},
        )

        summary = response.text.strip()

        # Optionally cache the summary in Firestore
        try:
            job_ref.update({"aiSummary": summary})
        except Exception as update_error:
            logger.warning("[summarize_snipe_logs] Failed to cache summary: %s", update_error)

        return success_response(SummaryData(summary=summary))

    except Exception as e:
        logger.error("[summarize_snipe_logs] Error: %s", e)
        return error_response(str(e), 500)
