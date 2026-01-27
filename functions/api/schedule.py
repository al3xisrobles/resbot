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


def _delete_scheduler_job(job_id: str):
    """
    Delete a Cloud Scheduler job by job ID.
    """
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}"
    job_name = f"{parent}/jobs/resy-snipe-{job_id}"
    
    try:
        get_scheduler_client().delete_job(request={"name": job_name})
        logger.info(f"[_delete_scheduler_job] Deleted scheduler job: {job_name}")
    except Exception as e:
        # Job might not exist, log but don't fail
        logger.warning(f"[_delete_scheduler_job] Failed to delete scheduler job {job_name}: {e}")


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


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def update_snipe(req: Request):
    """
    HTTP endpoint to update an existing reservation snipe job.
    
    Body should include:
      jobId (required)
      Any of: date, hour, minute, partySize, windowHours, seatingType, dropDate, dropHour, dropMinute
    
    Steps:
      1. Load existing job from Firestore
      2. Update job document with new values
      3. Delete old Cloud Scheduler job
      4. Create new Cloud Scheduler job with updated target time
    """
    try:
        data = req.get_json(silent=True) or {}
        job_id = data.get("jobId")
        
        if not job_id:
            return {"success": False, "error": "Missing jobId"}, 400
        
        # Load existing job
        job_ref = get_db().collection("reservationJobs").document(job_id)
        job_snap = job_ref.get()
        
        if not job_snap.exists:
            return {"success": False, "error": "Job not found"}, 404
        
        existing_job = job_snap.to_dict()
        
        # Only allow updates to pending jobs
        if existing_job.get("status") != "pending":
            return {"success": False, "error": "Can only update pending jobs"}, 400
        
        # Build update dict with only provided fields
        updates = {}
        
        # Reservation date
        if "date" in data:
            updates["date"] = data["date"]
        
        # Reservation time
        if "hour" in data:
            updates["hour"] = int(data["hour"])
        if "minute" in data:
            updates["minute"] = int(data["minute"])
        
        # Party size
        if "partySize" in data:
            updates["partySize"] = int(data["partySize"])
        
        # Window hours
        if "windowHours" in data:
            updates["windowHours"] = int(data["windowHours"])
        
        # Seating type
        if "seatingType" in data:
            updates["seatingType"] = data["seatingType"] if data["seatingType"] not in (None, "", "any") else None
        
        # Drop date and time (affects scheduler job)
        drop_date_str = data.get("dropDate", existing_job.get("dropDate"))
        drop_hour = int(data.get("dropHour", existing_job.get("dropHour")))
        drop_minute = int(data.get("dropMinute", existing_job.get("dropMinute")))
        
        if "dropDate" in data:
            updates["dropDate"] = drop_date_str
        if "dropHour" in data:
            updates["dropHour"] = drop_hour
        if "dropMinute" in data:
            updates["dropMinute"] = drop_minute
        
        # Recalculate target time if drop date/time changed
        if "dropDate" in data or "dropHour" in data or "dropMinute" in data:
            drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
            target_dt = dt.datetime(
                drop_year, drop_month, drop_day, drop_hour, drop_minute,
                tzinfo=ZoneInfo("America/New_York")
            )
            updates["targetTimeIso"] = target_dt.isoformat()
        
        # Update lastUpdate timestamp
        updates["lastUpdate"] = firestore.SERVER_TIMESTAMP
        
        # Update Firestore document
        job_ref.update(updates)
        
        # If drop date/time changed, update Cloud Scheduler job
        if "dropDate" in data or "dropHour" in data or "dropMinute" in data:
            # Delete old scheduler job
            _delete_scheduler_job(job_id)
            
            # Create new scheduler job with updated target time
            drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
            target_dt = dt.datetime(
                drop_year, drop_month, drop_day, drop_hour, drop_minute,
                tzinfo=ZoneInfo("America/New_York")
            )
            _create_scheduler_job(job_id, target_dt)
        
        # Return updated job data
        updated_snap = job_ref.get()
        updated_job = updated_snap.to_dict()
        
        return {
            "success": True,
            "jobId": job_id,
            "targetTimeIso": updated_job.get("targetTimeIso"),
        }, 200
        
    except Exception as e:
        logger.error(f"[update_snipe] Error: {e}")
        return {"success": False, "error": str(e)}, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def cancel_snipe(req: Request):
    """
    HTTP endpoint to cancel a reservation snipe job.
    
    Body should include:
      jobId (required)
    
    Steps:
      1. Load job from Firestore
      2. Delete Cloud Scheduler job
      3. Update Firestore document status to "cancelled"
    """
    try:
        data = req.get_json(silent=True) or {}
        job_id = data.get("jobId")
        
        if not job_id:
            return {"success": False, "error": "Missing jobId"}, 400
        
        # Load existing job
        job_ref = get_db().collection("reservationJobs").document(job_id)
        job_snap = job_ref.get()
        
        if not job_snap.exists:
            return {"success": False, "error": "Job not found"}, 404
        
        existing_job = job_snap.to_dict()
        
        # Only allow cancellation of pending jobs
        if existing_job.get("status") != "pending":
            return {"success": False, "error": "Can only cancel pending jobs"}, 400
        
        # Delete Cloud Scheduler job
        _delete_scheduler_job(job_id)
        
        # Update Firestore document status
        job_ref.update({
            "status": "cancelled",
            "lastUpdate": firestore.SERVER_TIMESTAMP,
        })
        
        return {
            "success": True,
            "jobId": job_id,
        }, 200
        
    except Exception as e:
        logger.error(f"[cancel_snipe] Error: {e}")
        return {"success": False, "error": str(e)}, 500
