"""
Scheduler Cloud Functions for Resy Bot
Handles creating Cloud Scheduler jobs for reservation sniping
"""

import os
import json
import datetime as dt
import logging
from zoneinfo import ZoneInfo

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import firestore

from google.cloud.scheduler_v1 import CloudSchedulerClient, HttpMethod

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("GCLOUD_PROJECT")
LOCATION_ID = os.environ.get("LOCATION_ID", "us-central1")
SNIPER_URL = "https://run-snipe-hypomglm7a-uc.a.run.app"

_db = None
_scheduler_client = None


def get_db():
    """Lazily get Firestore client so we don't require ADC at import time."""
    global _db
    if _db is None:
        _db = firestore.client()
    return _db


def get_scheduler_client():
    """Lazily get Cloud Scheduler client."""
    global _scheduler_client
    if _scheduler_client is None:
        _scheduler_client = CloudSchedulerClient()
    return _scheduler_client


def _create_scheduler_job(job_id: str, target_dt: dt.datetime):
    """
    Create a Cloud Scheduler job that will POST {jobId} to run_snipe
    at the correct minute for target_dt.

    NOTE: Cloud Scheduler only supports minute-level cron, so we:
      - schedule 1 minute BEFORE target_dt to account for cold start
      - run_snipe() then sleeps to hit exact second.
    """
    if not SNIPER_URL:
        raise RuntimeError("SNIPER_URL env var must be set to run_snipe's URL")

    parent = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}"
    job_name = f"{parent}/jobs/resy-snipe-{job_id}"

    # Schedule 1 minute early to account for cold start time
    schedule_dt = target_dt - dt.timedelta(minutes=1)

    # Cron format: "MIN HOUR DOM MON DOW"
    minute = schedule_dt.minute
    hour = schedule_dt.hour
    day = schedule_dt.day
    month = schedule_dt.month
    cron = f"{minute} {hour} {day} {month} *"

    body = json.dumps({"jobId": job_id}).encode("utf-8")

    job = {
        "name": job_name,
        "schedule": cron,
        "time_zone": "America/New_York",
        "http_target": {
            "uri": SNIPER_URL,
            "http_method": HttpMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "body": body,
        },
    }

    # Create the scheduler job (will throw if job_name already exists)
    get_scheduler_client().create_job(request={"parent": parent, "job": job})


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def create_snipe(req: Request):
    """
    HTTP endpoint your frontend calls to schedule a snipe.

    Body should include at least:
      venueId, partySize,
      date (YYYY-MM-DD)      -> date of the reservation itself
      dropDate (YYYY-MM-DD)  -> date the reservation DROPS on Resy
      hour, minute,          -> reservation time (for TimedReservationRequest)
      dropHour, dropMinute   -> drop time (when we should start sniping)

    Steps:
      1. Write job doc to Firestore
      2. Create a Cloud Scheduler HTTP job that will call run_snipe
         at the correct minute for dropDate + dropHour:dropMinute.
    """
    try:
        data = req.get_json(silent=True) or {}

        required_fields = [
            "venueId",
            "partySize",
            "date",       # reservation date
            "dropDate",   # drop date
            "hour",
            "minute",
            "dropHour",
            "dropMinute",
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"error": f"Missing fields: {', '.join(missing)}"}, 400

        # Reservation date (when you actually want to eat there)
        date_str = data["date"]  # "YYYY-MM-DD"

        # Drop date (when Resy releases the slot)
        drop_date_str = data["dropDate"]  # "YYYY-MM-DD"
        drop_hour = int(data["dropHour"])
        drop_minute = int(data["dropMinute"])

        # Parse drop date string -> target datetime (local time, e.g. America/New_York)
        drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
        target_dt = dt.datetime(
            drop_year, drop_month, drop_day, drop_hour, drop_minute,
            tzinfo=ZoneInfo("America/New_York")
        )

        # Prepare job doc
        job_ref = get_db().collection("reservationJobs").document()
        job_id = job_ref.id

        job_data = {
            "jobId": job_id,
            "userId": data.get("userId"),
            "venueId": data["venueId"],
            "partySize": int(data["partySize"]),
            # Reservation info
            "date": date_str,
            "hour": int(data["hour"]),
            "minute": int(data["minute"]),
            # Drop info
            "dropDate": drop_date_str,
            "dropHour": drop_hour,
            "dropMinute": drop_minute,
            # Job/meta
            "status": "pending",
            "targetTimeIso": target_dt.isoformat(),  # run_snipe uses this
            "createdAt": firestore.SERVER_TIMESTAMP,
            "lastUpdate": firestore.SERVER_TIMESTAMP,
            # Extra options
            "windowHours": int(data.get("windowHours", 1)),
            "seatingType": data.get("seatingType"),
        }

        job_ref.set(job_data)

        # Create one Cloud Scheduler job that will call run_snipe
        _create_scheduler_job(job_id, target_dt)

        return {
            "success": True,
            "jobId": job_id,
            "targetTimeIso": job_data["targetTimeIso"],
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500
