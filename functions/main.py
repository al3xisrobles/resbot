"""
Firebase Python Cloud Functions for Resy Bot
These functions can call code from resy_client/ module
"""

# Fix macOS fork crash issue - must be done BEFORE any other imports
# that might use multiprocessing or SSL
import multiprocessing
import sys
if sys.platform == "darwin":  # macOS
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # Already set

import os
import logging
from dotenv import load_dotenv

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, set_global_options
from firebase_admin import initialize_app

# Bind Secret Manager secrets to every function so they are injected as environment
# variables at runtime (read below and in the api modules via os.getenv). Values live
# in GCP Secret Manager, set once with `firebase functions:secrets:set <NAME>`, never
# in source or CI. This must run before importing the function modules below, whose
# decorators read the global options at import time.
set_global_options(secrets=[
    "GEMINI_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "SENTRY_DSN",
    "RESY_DEBUG_EMAIL",
    "RESY_DEBUG_PASSWORD",
    "RESEND_API_KEY",
    "RESEND_FROM_ADDRESS",
])

# Import all Cloud Functions from other modules so Firebase can discover them
from api.search import search, search_map  # noqa: F401, E402
from api.venue import check_venue_payment_requirement, venue, venue_links  # noqa: F401, E402
from api.reservations import calendar, reservation, slots  # noqa: F401, E402
from api.featured import climbing, top_rated  # noqa: F401, E402
from api.gemini_search import gemini_search  # noqa: F401, E402
from api.snipe import run_snipe, run_discovery_snipe, summarize_snipe_logs  # noqa: F401, E402
from api.schedule import create_snipe, update_snipe, cancel_snipe  # noqa: F401, E402
from api.watch import run_watch_tick, seed_watch_tick  # noqa: F401, E402
from api.onboarding import start_resy_onboarding, resy_account  # noqa: F401, E402
from api.me import me  # noqa: F401, E402
from api.debug import resy_debug  # noqa: F401, E402

# Initialize Firebase Admin (Firestore, etc.)
initialize_app()

# Load environment variables from .env file
load_dotenv()

# Setup logging for GCP Cloud Functions
# GCP automatically captures stdout/stderr, so we configure logging to use stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
)
logger = logging.getLogger(__name__)

# Initialize Sentry SDK for error tracking and distributed tracing
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,  # 100% sampling for all requests
        send_default_pii=True,  # Match frontend setting
        integrations=[
            FlaskIntegration(),
        ],
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info("Sentry SDK initialized with 100% trace sampling")
else:
    logger.warning("SENTRY_DSN not set - Sentry monitoring disabled")


logger.info("OBJC_DISABLE_INITIALIZE_FORK_SAFETY=%r", os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY"))
logger.info("GUNICORN_CMD_ARGS=%r", os.environ.get("GUNICORN_CMD_ARGS"))

@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def health(req: Request):
    """
    Health check endpoint
    GET /health

    Returns a simple health status to verify the function is running
    """
    return {
        "status": "ok",
        "message": "Resy Bot Cloud Functions are running!",
        "timestamp": None,
    }
