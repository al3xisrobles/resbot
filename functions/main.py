"""
Firebase Python Cloud Functions for Resy Bot
These functions can call code from resy_client/ module
"""

import logging

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import initialize_app

# Import all Cloud Functions from other modules so Firebase can discover them
from api.search import search, search_map  # noqa: F401
from api.venue import venue, venue_links, venue_photo, venue_photo_proxy  # noqa: F401
from api.reservations import calendar, reservation  # noqa: F401
from api.featured import climbing, top_rated  # noqa: F401
from api.gemini_search import gemini_search  # noqa: F401
from api.snipe import run_snipe  # noqa: F401
from api.schedule import create_snipe  # noqa: F401

# Initialize Firebase Admin (Firestore, etc.)
initialize_app()

# Setup logging for GCP Cloud Functions
# GCP automatically captures stdout/stderr, so we configure logging to use stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


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
