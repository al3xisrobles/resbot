"""
Quick test script: send a failure notification email from a real Firestore job document.

Usage (from the functions/ directory with venv active):
    python test_email.py <jobId> [--gemini]

Examples:
    python test_email.py abc123xyz             # uses raw errorMessage from Firestore
    python test_email.py abc123xyz --gemini    # calls Gemini to generate the email summary

The script reads the real job doc from Firestore, loads the user's Resy credentials,
looks up the venue name, and fires the email via Resend.
It prints a full diagnostic so you can see exactly what would be sent.
"""

import sys
import os
from dotenv import load_dotenv

# Load .env before anything else so RESEND_API_KEY etc. are available
load_dotenv()

# Always target production Firestore — unset emulator env vars that may be
# inherited from a running `firebase functions:shell` or emulator session.
os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
os.environ.pop("FIREBASE_EMULATOR_HUB", None)

import firebase_admin
from firebase_admin import firestore
from firebase_admin import initialize_app

initialize_app()

# pylint: disable=wrong-import-position
from api.email import send_failed_reservation_email
from api.utils import load_credentials


def main():
    args = sys.argv[1:]
    use_gemini = "--gemini" in args
    positional = [a for a in args if not a.startswith("--")]

    if not positional:
        print("Usage: python test_email.py <jobId> [--gemini]")
        print("  jobId    : Firestore document ID from the reservationJobs collection")
        print("  --gemini : call Gemini to generate the email summary (mirrors production)")
        sys.exit(1)

    job_id = positional[0].strip()
    print(f"\n{'='*60}")
    print(f"  Testing failure email for job: {job_id}")
    print(f"  Summary mode: {'Gemini (production-like)' if use_gemini else 'raw errorMessage'}")
    print(f"{'='*60}\n")

    db = firestore.client()

    # ── 1. Load the job document ──────────────────────────────────
    print("[ 1/4 ] Loading job from Firestore...")
    snap = db.collection("reservationJobs").document(job_id).get()
    if not snap.exists:
        print(f"  ✗ Job '{job_id}' not found in reservationJobs.")
        sys.exit(1)

    job = snap.to_dict()
    print("  ✓ Found job")
    print(f"        status     : {job.get('status')}")
    print(f"        venueId    : {job.get('venueId')}")
    print(f"        date       : {job.get('date')}")
    print(f"        time       : {job.get('hour')}:{str(job.get('minute', 0)).zfill(2)}")
    print(f"        partySize  : {job.get('partySize')}")
    print(f"        userId     : {job.get('userId')}")
    print(f"        errorMsg   : {job.get('errorMessage')}")

    user_id = job.get("userId")
    if not user_id:
        print("\n  ✗ Job has no userId — cannot load credentials.")
        sys.exit(1)

    # ── 2. Load user credentials ──────────────────────────────────
    print("\n[ 2/4 ] Loading Resy credentials for user...")
    credentials = load_credentials(user_id)
    if not credentials:
        print("  ✗ No credentials found for userId:", user_id)
        sys.exit(1)

    user_email = credentials.get("email")
    user_first_name = credentials.get("firstName") or "Alexis"
    print("  ✓ Credentials loaded")
    print(f"        email      : {user_email}")
    print(f"        firstName  : {user_first_name}")

    if not user_email:
        print("\n  ✗ Credentials have no email address.")
        sys.exit(1)

    # ── 3. Look up venue name ─────────────────────────────────────
    print("\n[ 3/4 ] Looking up venue name...")
    venue_id = str(job.get("venueId", ""))
    venue_name = venue_id
    if venue_id:
        venue_snap = db.collection("venues").document(venue_id).get()
        if venue_snap.exists:
            venue_name = venue_snap.to_dict().get("venueName") or venue_id
            print(f"  ✓ Venue name: {venue_name}")
        else:
            print(f"  ⚠  No venue doc found for id={venue_id}, using id as fallback")
    else:
        print("  ⚠  No venueId on job, using empty string")

    # ── 4. Build email summary ────────────────────────────────────
    print("\n[ 4/4 ] Sending email via Resend...")
    print(f"        from       : {os.getenv('RESEND_FROM_ADDRESS', '(default)')}")
    print(f"        to         : {user_email}")
    print(f"        subject    : Your reservation attempt at {venue_name} was unsuccessful")

    if use_gemini:
        print("        summary    : generating via Gemini...")
        # pylint: disable=wrong-import-position
        from api.snipe import _generate_email_summary
        execution_logs = job.get("executionLogs") or []
        email_summary = _generate_email_summary(execution_logs, job.get("errorMessage"))
    else:
        email_summary = (
            job.get("errorMessage")
            or "The reservation could not be completed at this time."
        )

    print(f"        summary    : {email_summary[:80]}{'...' if len(email_summary) > 80 else ''}")

    result = send_failed_reservation_email(
        user_email=user_email,
        user_first_name=user_first_name,
        venue_name=venue_name,
        reservation_date=job.get("date", "2026-01-01"),
        reservation_hour=int(job.get("hour", 19)),
        reservation_minute=int(job.get("minute", 0)),
        party_size=int(job.get("partySize", 2)),
        job_id=job_id,
        email_summary=email_summary,
    )

    print()
    if result:
        print("  ✅ Email sent successfully — check your inbox and the Resend dashboard.")
    else:
        print("  ✗  Email failed — check the error output above and verify:")
        print("       • RESEND_API_KEY is set in functions/.env")
        print("       • RESEND_FROM_ADDRESS uses a verified domain in Resend")
        print("       • The recipient address is not on the suppression list")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
