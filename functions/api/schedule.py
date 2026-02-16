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

from .sentry_utils import with_sentry_trace
from .response_schemas import (
    success_response,
    error_response,
    JobCreatedData,
    JobUpdatedData,
    JobCancelledData,
)
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


def _create_scheduler_job(job_id: str, target_dt: dt.datetime, timezone: str = "America/New_York") -> dt.datetime:
    """
    Create a Cloud Scheduler job that will POST {jobId} to run_snipe
    at the correct minute for target_dt.

    NOTE: Cloud Scheduler only supports minute-level cron, so we:
      - schedule 1 minute BEFORE target_dt to account for cold start
      - run_snipe() then sleeps to hit exact second.
      - BUT: we don't shift to a different day (to avoid date bugs)
    
    Args:
        job_id: Unique identifier for the job
        target_dt: Target datetime for the snipe (in the specified timezone)
        timezone: IANA timezone string (e.g., "America/New_York", "America/Los_Angeles")
    
    Returns:
        The scheduled run time (datetime) from Cloud Scheduler
    
    Raises:
        ValueError: If the scheduled run time doesn't match the expected date
    """
    if not SNIPER_URL:
        raise RuntimeError("SNIPER_URL env var must be set to run_snipe's URL")

    parent = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}"
    job_name = f"{parent}/jobs/resy-snipe-{job_id}"

    # Schedule 1 minute early to account for cold start time,
    # BUT don't shift to a different day (avoid midnight edge case bugs)
    schedule_dt = target_dt - dt.timedelta(minutes=1)
    if schedule_dt.date() != target_dt.date():
        # If subtracting 1 minute would change the day, use the target time instead
        # (e.g., target is 00:00, don't schedule for 23:59 the day before)
        schedule_dt = target_dt
        logger.info(f"[_create_scheduler_job] Midnight edge case: using target_dt directly to avoid day shift")

    # Cron format: "MIN HOUR DOM MON DOW"
    minute = schedule_dt.minute
    hour = schedule_dt.hour
    day = schedule_dt.day
    month = schedule_dt.month
    year = schedule_dt.year
    cron = f"{minute} {hour} {day} {month} *"

    body = json.dumps({"jobId": job_id}).encode("utf-8")

    job = {
        "name": job_name,
        "schedule": cron,
        "time_zone": timezone,  # Use the city's timezone
        "http_target": {
            "uri": SNIPER_URL,
            "http_method": HttpMethod.POST,
            "headers": {"Content-Type": "application/json"},
            "body": body,
        },
    }

    logger.info(f"[_create_scheduler_job] Creating job {job_id} with cron '{cron}' in timezone '{timezone}'")
    logger.info(f"[_create_scheduler_job] Expected to run on {year}-{month:02d}-{day:02d} at {hour:02d}:{minute:02d}")
    logger.info(f"[_create_scheduler_job] Original target_dt was: {target_dt.isoformat()}")

    # Create the scheduler job and get the response
    created_job = get_scheduler_client().create_job(request={"parent": parent, "job": job})
    
    # Validate that Cloud Scheduler will run this on the expected date
    if created_job.schedule_time:
        scheduled_run_time = created_job.schedule_time
        # Convert to the target timezone to compare dates
        tz_info = ZoneInfo(timezone)
        scheduled_in_tz = scheduled_run_time.astimezone(tz_info)
        
        logger.info(f"[_create_scheduler_job] Cloud Scheduler reports next run: {scheduled_in_tz.isoformat()}")
        
        # Check if the scheduled date matches what we expect
        if scheduled_in_tz.date() != schedule_dt.date():
            # This would happen if Cloud Scheduler schedules for next year
            error_msg = (
                f"Cloud Scheduler date mismatch! Expected {schedule_dt.date()} "
                f"but got {scheduled_in_tz.date()}. "
                f"This usually means the date has already passed."
            )
            logger.error(f"[_create_scheduler_job] {error_msg}")
            # Delete the incorrectly scheduled job
            try:
                get_scheduler_client().delete_job(request={"name": job_name})
            except Exception:
                pass
            raise ValueError(error_msg)
        
        return scheduled_in_tz
    
    return schedule_dt


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
@with_sentry_trace
def create_snipe(req: Request):
    """
    HTTP endpoint your frontend calls to schedule a snipe.

    Body should include at least:
      venueId, partySize,
      date (YYYY-MM-DD)      -> date of the reservation itself
      dropDate (YYYY-MM-DD)  -> date the reservation DROPS on Resy
      hour, minute,          -> reservation time (for TimedReservationRequest)
      dropHour, dropMinute   -> drop time (when we should start sniping)
      timezone (optional)    -> IANA timezone string (e.g., "America/Los_Angeles")

    Steps:
      1. Write job doc to Firestore
      2. Create a Cloud Scheduler HTTP job that will call run_snipe
         at the correct minute for dropDate + dropHour:dropMinute.
    """
    try:
        data = req.get_json(silent=True) or {}
        
        # Log the raw request data for debugging
        logger.info(f"[create_snipe] Received request data: {json.dumps(data, default=str)}")

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

        # Get timezone from request, default to America/New_York for backwards compatibility
        timezone = data.get("timezone", "America/New_York")
        
        # Validate timezone is a known IANA timezone
        try:
            tz_info = ZoneInfo(timezone)
        except Exception:
            logger.warning(f"[create_snipe] Invalid timezone '{timezone}', falling back to America/New_York")
            timezone = "America/New_York"
            tz_info = ZoneInfo(timezone)

        # Parse drop date string -> target datetime in the specified timezone
        drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
        target_dt = dt.datetime(
            drop_year, drop_month, drop_day, drop_hour, drop_minute,
            tzinfo=tz_info
        )
        
        # Extensive logging for debugging timezone issues
        logger.info(f"[create_snipe] Parsed drop date: year={drop_year}, month={drop_month}, day={drop_day}")
        logger.info(f"[create_snipe] Drop time: {drop_hour}:{drop_minute:02d}")
        logger.info(f"[create_snipe] Using timezone: {timezone}")
        logger.info(f"[create_snipe] target_dt = {target_dt.isoformat()}")
        logger.info(f"[create_snipe] target_dt.date() = {target_dt.date()}")
        
        # Validate that the target time is in the future
        now_in_tz = dt.datetime.now(tz_info)
        logger.info(f"[create_snipe] Current time in {timezone}: {now_in_tz.isoformat()}")
        
        if target_dt <= now_in_tz:
            logger.warning(f"[create_snipe] Rejected: target_dt ({target_dt.isoformat()}) <= now ({now_in_tz.isoformat()})")
            return {
                "error": f"Drop time must be in the future. Got {target_dt.isoformat()}, current time is {now_in_tz.isoformat()}"
            }, 400
        
        logger.info(f"[create_snipe] Validation passed: target is in the future")

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
            "targetTimeIso": target_dt.isoformat(),  # run_snipe uses this (includes timezone offset)
            "timezone": timezone,  # Store timezone for reference and updates
            "createdAt": firestore.SERVER_TIMESTAMP,
            "lastUpdate": firestore.SERVER_TIMESTAMP,
            # Extra options
            "windowHours": int(data.get("windowHours", 1)),
            "seatingType": data.get("seatingType"),
        }

        job_ref.set(job_data)

        # Create one Cloud Scheduler job that will call run_snipe
        try:
            scheduled_time = _create_scheduler_job(job_id, target_dt, timezone)
            logger.info(f"[create_snipe] Successfully scheduled job {job_id} for {scheduled_time.isoformat()}")
        except ValueError as e:
            # Scheduler validation failed (e.g., date mismatch) - delete the Firestore doc
            logger.error(f"[create_snipe] Scheduler validation failed: {e}")
            job_ref.delete()
            return error_response(str(e), 400)

        return success_response(
            JobCreatedData(
                jobId=job_id,
                targetTimeIso=job_data["targetTimeIso"],
            )
        ), 200

    except Exception as e:
        logger.error(f"[create_snipe] Unexpected error: {e}")
        return error_response(str(e), 500)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
@with_sentry_trace
def update_snipe(req: Request):
    """
    HTTP endpoint to update an existing reservation snipe job.
    
    Body should include:
      jobId (required)
      Any of: date, hour, minute, partySize, windowHours, seatingType, dropDate, dropHour, dropMinute, timezone
    
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
            return error_response("Can only update pending jobs", 400)
        
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
        
        # Get timezone from request or existing job, default to America/New_York
        timezone = data.get("timezone", existing_job.get("timezone", "America/New_York"))
        if "timezone" in data:
            updates["timezone"] = timezone
        
        # Validate timezone
        try:
            tz_info = ZoneInfo(timezone)
        except Exception:
            logger.warning(f"[update_snipe] Invalid timezone '{timezone}', falling back to America/New_York")
            timezone = "America/New_York"
            tz_info = ZoneInfo(timezone)
        
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
        
        # Recalculate target time if drop date/time/timezone changed
        if "dropDate" in data or "dropHour" in data or "dropMinute" in data or "timezone" in data:
            drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
            target_dt = dt.datetime(
                drop_year, drop_month, drop_day, drop_hour, drop_minute,
                tzinfo=tz_info
            )
            
            # Validate that the new target time is in the future
            now_in_tz = dt.datetime.now(tz_info)
            if target_dt <= now_in_tz:
                return {
                    "success": False,
                    "error": f"Drop time must be in the future. Got {target_dt.isoformat()}, current time is {now_in_tz.isoformat()}"
                }, 400
            
            updates["targetTimeIso"] = target_dt.isoformat()
        
        # Update lastUpdate timestamp
        updates["lastUpdate"] = firestore.SERVER_TIMESTAMP
        
        # If drop date/time/timezone changed, update Cloud Scheduler job FIRST (before updating Firestore)
        if "dropDate" in data or "dropHour" in data or "dropMinute" in data or "timezone" in data:
            # Delete old scheduler job
            _delete_scheduler_job(job_id)
            
            # Create new scheduler job with updated target time
            drop_year, drop_month, drop_day = map(int, drop_date_str.split("-"))
            target_dt = dt.datetime(
                drop_year, drop_month, drop_day, drop_hour, drop_minute,
                tzinfo=tz_info
            )
            try:
                scheduled_time = _create_scheduler_job(job_id, target_dt, timezone)
                logger.info(f"[update_snipe] Successfully rescheduled job {job_id} for {scheduled_time.isoformat()}")
            except ValueError as e:
                # Scheduler validation failed - don't update Firestore
                logger.error(f"[update_snipe] Scheduler validation failed: {e}")
                return error_response(str(e), 400)
        
        # Update Firestore document (only after scheduler job is successfully created)
        job_ref.update(updates)
        
        # Return updated job data
        updated_snap = job_ref.get()
        updated_job = updated_snap.to_dict()
        
        return success_response(
            JobUpdatedData(
                jobId=job_id,
                targetTimeIso=updated_job.get("targetTimeIso"),
            )
        ), 200
        
    except Exception as e:
        logger.error(f"[update_snipe] Error: {e}")
        return error_response(str(e), 500)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
@with_sentry_trace
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
            return error_response("Missing jobId", 400)
        
        # Load existing job
        job_ref = get_db().collection("reservationJobs").document(job_id)
        job_snap = job_ref.get()
        
        if not job_snap.exists:
            return error_response("Job not found", 404)
        
        existing_job = job_snap.to_dict()
        
        # Only allow cancellation of pending jobs
        if existing_job.get("status") != "pending":
            return error_response("Can only cancel pending jobs", 400)
        
        # Delete Cloud Scheduler job
        _delete_scheduler_job(job_id)
        
        # Update Firestore document status
        job_ref.update({
            "status": "cancelled",
            "lastUpdate": firestore.SERVER_TIMESTAMP,
        })
        
        return success_response(JobCancelledData(jobId=job_id)), 200
        
    except Exception as e:
        logger.error(f"[cancel_snipe] Error: {e}")
        return error_response(str(e), 500)
