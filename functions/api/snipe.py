"""
Sniper Cloud Function for Resy Bot
Handles the actual reservation sniping at precise drop times
"""

import time
import datetime as dt
import logging

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import firestore
from google.cloud import firestore as gc_firestore

from .resy_client.models import ResyConfig, ReservationRequest
from .resy_client.manager import ResyManager
from .utils import load_credentials

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
    logger.info(f"[run_snipe] Starting reservation for job {job_data.get('jobId')} at {dt.datetime.now().isoformat()}")
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
)
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
        return {"error": "Method not allowed"}, 405

    try:
        logger.info("[run_snipe] Received request")
        logger.info(f"[run_snipe] method={req.method}")
        body = req.get_json(silent=True) or {}
        job_id = body.get("jobId")
        print(f"[run_snipe] Request body: {body}")
        if not job_id:
            return {"error": "Missing jobId"}, 400

        job_ref = get_db().collection("reservationJobs").document(job_id)
        snap = job_ref.get()
        if not snap.exists:
            logger.error(f"[run_snipe] Job {job_id} not found")
            return {"error": "Job not found"}, 404

        job_data = snap.to_dict()
        user_id = job_data.get('userId')
        print(f"[run_snipe] Job loaded, userId: {user_id}")

        # targetTimeIso stored as ISO 8601 with timezone, e.g. "2025-12-01T00:00:00-05:00"
        target_iso = job_data.get("targetTimeIso")
        if not target_iso:
            return {"error": "Job missing targetTimeIso"}, 400

        target_dt = dt.datetime.fromisoformat(target_iso)
        now = dt.datetime.now(tz=target_dt.tzinfo)
        # Cloud Scheduler triggers ~1 min early, so we sleep until 0.1s before target
        delta_seconds = (target_dt - now).total_seconds() - 0.1

        logger.info(f"[run_snipe] Current time: {now.isoformat()}")
        logger.info(f"[run_snipe] Target time: {target_dt.isoformat()}")

        if delta_seconds > 0:
            logger.info(f"[run_snipe] Sleeping for {delta_seconds:.2f} seconds until target time")
            time.sleep(delta_seconds)

        # Attempt reservation for ~30 seconds max
        success = False
        resy_token = None
        deadline_seconds = 30
        start = time.time()

        while time.time() - start < deadline_seconds:
            try:
                resy_token = _make_reservation_for_job(job_data, user_id)
                success = True
                logger.info(f"[run_snipe] ✓ Reservation successful!")
                break
            except Exception as inner_e:
                elapsed = time.time() - start
                logger.warning(f"[run_snipe] ✗ Attempt failed after {elapsed:.2f}s: {inner_e}")
                # Backoff a bit before retrying
                if elapsed < deadline_seconds:
                    time.sleep(0.1)

        status = "done" if success else "failed"
        logger.info(f"[run_snipe] Reservation attempt completed with status: {status}")

        job_ref.update(
            {
                "status": status,
                "lastUpdate": gc_firestore.SERVER_TIMESTAMP,
                "resyToken": resy_token if success else None,
            }
        )

        return {
            "status": status,
            "jobId": job_id,
            "resyToken": resy_token,
        }

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
                    }
                )
        except Exception:
            pass

        return {"error": str(e)}, 500
