"""
Sniper Cloud Function for Resy Bot
Handles the actual reservation sniping at precise drop times
"""

import time
import datetime as dt
import logging

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption
from firebase_admin import firestore
from google.cloud import firestore as gc_firestore

from .sentry_utils import with_sentry_trace
from .resy_client.models import ResyConfig, ReservationRequest
from .resy_client.manager import ResyManager
from .resy_client.errors import RateLimitError
from .constants import GEMINI_MODEL
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


def _make_reservation_for_job(job_data: dict, user_id: str = None, use_parallel: bool = True) -> str:
    """
    Execute the reservation attempt using job_data stored in Firestore.
    Returns the resy_token (or raises on error).

    Args:
        job_data: Job configuration from Firestore
        user_id: User ID for loading credentials
        use_parallel: If True, attempts to book top 3 slots in parallel for speed
    """
    logger.info("[run_snipe] Starting reservation for job %s at %s", job_data.get("jobId"), dt.datetime.now().isoformat())
    reservation_request, manager = _build_reservation_request_from_dict(job_data, user_id)

    if use_parallel:
        logger.info("[run_snipe] Using parallel booking strategy")
        resy_token = manager.make_reservation_parallel_with_retries(reservation_request, n_slots=3)
    else:
        resy_token = manager.make_reservation_with_retries(reservation_request)
    return resy_token


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
    Query parameters:
    - userId: User ID (optional) - if provided, loads credentials from Firestore

    Steps:
      1. Load job from Firestore
      2. Sleep until targetTime - 5 seconds
      3. Call _make_reservation_for_job()
      4. Update job status in Firestore
    """
    # 1) Let preflight succeed without touching JSON
    if req.method == "OPTIONS":
        # CORS wrapper adds headers; empty 204 is fine
        return ("", 204)

    # 2) Only process real POSTs
    if req.method != "POST":
        print(f"[run_snipe] ✗ Method not allowed: {req.method}")
        return error_response("Method not allowed", 405)

    try:
        logger.info("[run_snipe] Received request")
        logger.info("[run_snipe] method=%s", req.method)
        body = req.get_json(silent=True) or {}
        job_id = body.get("jobId")
        print(f"[run_snipe] Request body: {body}")
        if not job_id:
            return error_response("Missing jobId", 400)

        job_ref = get_db().collection("reservationJobs").document(job_id)
        snap = job_ref.get()
        if not snap.exists:
            logger.error("[run_snipe] Job %s not found", job_id)
            return error_response("Job not found", 404)

        job_data = snap.to_dict()
        user_id = job_data.get('userId')
        print(f"[run_snipe] Job loaded, userId: {user_id}")

        # targetTimeIso stored as ISO 8601 with timezone, e.g. "2025-12-01T00:00:00-05:00"
        target_iso = job_data.get("targetTimeIso")
        if not target_iso:
            return error_response("Job missing targetTimeIso", 400)

        target_dt = dt.datetime.fromisoformat(target_iso)
        now = dt.datetime.now(tz=target_dt.tzinfo)
        # Cloud Scheduler triggers ~1 min early, so we sleep until 0.1s before target
        delta_seconds = (target_dt - now).total_seconds() - 0.1

        logger.info("[run_snipe] Current time: %s", now.isoformat())
        logger.info("[run_snipe] Target time: %s", target_dt.isoformat())

        if delta_seconds > 0:
            logger.info("[run_snipe] Sleeping for %.2f seconds until target time", delta_seconds)
            time.sleep(delta_seconds)

        # Attempt reservation for ~30 seconds max
        success = False
        resy_token = None
        deadline_seconds = 30
        start = time.time()

        # Track execution logs
        execution_logs = []
        last_error = None

        # Rate limit tracking for outer loop
        rate_limit_count = 0
        base_backoff = 0.5  # Start with 0.5s for non-rate-limit errors

        while time.time() - start < deadline_seconds:
            try:
                resy_token = _make_reservation_for_job(job_data, user_id)
                success = True
                logger.info("[run_snipe] ✓ Reservation successful!")
                execution_logs.append({
                    "timestamp": dt.datetime.now().isoformat(),
                    "status": "success",
                    "message": "Reservation successful"
                })
                break
            except RateLimitError as rate_err:
                # Handle rate limiting with longer backoff
                rate_limit_count += 1
                last_error = str(rate_err)
                elapsed = time.time() - start

                # Exponential backoff: 2s, 4s, 8s (capped)
                wait_time = min(2 * (2 ** (rate_limit_count - 1)), 8)
                remaining = deadline_seconds - elapsed

                logger.warning(
                    f"[run_snipe] ✗ Rate limited (#{rate_limit_count}) after {elapsed:.2f}s. "
                    f"Waiting {wait_time:.1f}s before retry. {remaining:.1f}s remaining."
                )
                execution_logs.append({
                    "timestamp": dt.datetime.now().isoformat(),
                    "status": "rate_limited",
                    "message": f"Rate limited - waiting {wait_time:.1f}s",
                    "elapsed_seconds": round(elapsed, 2)
                })

                # Don't sleep if we'd exceed the deadline
                if elapsed + wait_time < deadline_seconds:
                    time.sleep(wait_time)
                else:
                    # Not enough time to wait and retry meaningfully
                    logger.info("[run_snipe] Not enough time remaining after rate limit. Exiting.")
                    break

            except Exception as inner_e:
                last_error = str(inner_e)
                elapsed = time.time() - start
                logger.warning("[run_snipe] ✗ Attempt failed after %.2f s: %s", elapsed, inner_e)
                execution_logs.append({
                    "timestamp": dt.datetime.now().isoformat(),
                    "status": "error",
                    "message": str(inner_e),
                    "elapsed_seconds": round(elapsed, 2)
                })
                # Modest backoff for other errors
                if elapsed < deadline_seconds:
                    time.sleep(base_backoff)

        status = "done" if success else "failed"
        logger.info("[run_snipe] Reservation attempt completed with status: %s", status)

        job_ref.update(
            {
                "status": status,
                "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
                "resyToken": resy_token if success else None,
                "errorMessage": last_error if not success else None,
                "executionLogs": execution_logs,
            }
        )

        return success_response(
            SnipeResultData(status=status, jobId=job_id, resyToken=resy_token)
        )

    except Exception as e:
        # best-effort logging & marking as failed
        try:
            body = req.get_json(silent=True) or {}
            job_id = body.get("jobId")
            if job_id:
                get_db().collection("reservationJobs").document(job_id).update(
                    {
                        "status": "error",
                        "errorMessage": str(e),
                        "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
                        "executionLogs": [{
                            "timestamp": dt.datetime.now().isoformat(),
                            "status": "error",
                            "message": f"Exception during snipe execution: {str(e)}"
                        }],
                    }
                )
        except Exception:
            pass

        return error_response(str(e), 500)


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
