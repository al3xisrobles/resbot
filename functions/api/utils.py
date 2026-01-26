"""
Shared utility functions for Resy Bot Cloud Functions
Includes credential loading, search caching, and Resy API helpers
"""

import json
import logging
import os
import time as time_module
import traceback
from datetime import datetime
from hashlib import md5
from time import time

import requests
from firebase_admin import firestore
from google import genai

from .resy_client.models import FindRequestBody, ResyConfig
from .resy_client.api_access import ResyApiAccess

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Firestore client for progress updates (lazily initialized)
_firestore_client = None


def _get_firestore_client():
    """Lazily get Firestore client"""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.client()
    return _firestore_client


def update_search_progress(job_id: str | None, data: dict) -> None:
    """
    Update Firestore document with search job progress.

    Args:
        job_id: Optional job ID. If None, this is a no-op.
        data: Dict of progress data to merge into the document.
    """
    if not job_id:
        print("[PROGRESS] No job_id provided, skipping progress update")
        return

    print(f"[PROGRESS] Updating job {job_id} with data: {data}")
    try:
        db = _get_firestore_client()
        db.collection("searchJobs").document(job_id).set(data, merge=True)
    except Exception as e:
        # Don't let progress updates break the main search flow
        print(f"[PROGRESS] Error updating job {job_id}: {str(e)}")


# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
TRANSIENT_STATUS_CODES = {500, 502}

# Search results cache with TTL (5 minutes)
# Format: {cache_key: {'results': [...], 'total': int, 'timestamp': float}}
SEARCH_CACHE = {}
SEARCH_CACHE_TTL = 300  # 5 minutes in seconds

# Initialize Gemini AI client if API key is available
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def is_emulator() -> bool:
    # Any of these being set basically implies you're in `firebase emulators:start`
    return any(
        os.getenv(name)
        for name in [
            "FIREBASE_EMULATOR_HUB",
            "FIRESTORE_EMULATOR_HOST",
            "FIREBASE_AUTH_EMULATOR_HOST",
            "STORAGE_EMULATOR_HOST",
        ]
    )

if is_emulator():
    logger.info("⚠ Running in Firebase Emulator mode")
    CLOUD_FUNCTIONS_BASE = "http://127.0.0.1:5001/resybot-bd2db/us-central1"
else:
    logger.info("✓ Running in Production mode")
    CLOUD_FUNCTIONS_BASE = "https://us-central1-resybot-bd2db.cloudfunctions.net"


def load_credentials(userId=None):
    """
    Load Resy credentials from Firestore or environment variables

    Args:
        userId: Firebase user ID. If provided, loads from Firestore.
                If None, loads from environment variables (for public endpoints).

    Returns:
        dict: Credentials containing api_key, token, etc.

    Note:
        The Firestore document uses camelCase field names (apiKey, paymentMethodId)
        but this function returns snake_case for backwards compatibility
    """
    # If userId is provided, load from Firestore
    if userId:
        try:
            db = firestore.client()
            doc = db.collection('resyCredentials').document(userId).get()

            if not doc.exists:
                logger.warning("✗ No Resy credentials found in Firestore for user %s", userId)
                raise ValueError(f"User {userId} has not connected their Resy account")

            # Get the Firestore data (uses camelCase)
            data = doc.to_dict()

            # Transform to snake_case for backwards compatibility with existing code
            credentials = {
                'api_key': data.get('apiKey'),
                'token': data.get('token'),
                'payment_method_id': data.get('paymentMethodId'),
                'email': data.get('email'),
                'password': None,  # Never stored
                'guest_id': data.get('guestId'),
                'user_id': data.get('userId'),
                'first_name': data.get('firstName'),
                'last_name': data.get('lastName'),
                'mobile_number': data.get('mobileNumber'),
                'payment_methods': data.get('paymentMethods', []),
                'legacy_token': data.get('legacyToken')
            }

            logger.info("✓ Loaded Resy credentials from Firestore for user %s", userId)
            return credentials

        except Exception as e:
            logger.error("✗ Error loading credentials from Firestore: %s", e)
            raise

    # If userId is not provided, try to load from environment variables
    # This allows public endpoints to work without user authentication
    # Use the same default API key as in onboarding.py
    api_key = os.getenv('RESY_API_KEY', 'VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5')
    token = os.getenv('RESY_TOKEN', '')

    if not token:
        logger.info("ℹ No RESY_TOKEN provided, using API key only (suitable for public endpoints)")

    credentials = {
        'api_key': api_key,
        'token': token,  # Empty string if not provided
        'payment_method_id': None,
        'email': None,
        'password': None,
        'guest_id': None,
        'user_id': None,
        'first_name': None,
        'last_name': None,
        'mobile_number': None,
        'payment_methods': [],
        'legacy_token': None
    }

    logger.info("✓ Loaded Resy credentials from environment variables (default API key)")
    return credentials


def get_resy_headers(config):
    """Build Resy API headers"""
    headers = {
        'Authorization': f'ResyAPI api_key="{config["api_key"]}"',
        'Origin': 'https://resy.com',
        'X-origin': 'https://resy.com',
        'Referer': 'https://resy.com/',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Content-Type': 'application/json'
    }

    # Only add auth token headers if token is provided
    token = config.get('token')
    if token:
        headers['X-Resy-Auth-Token'] = token
        headers['X-Resy-Universal-Auth'] = token

    return headers


def get_search_cache_key(query, filters, geo_config, include_availability=False):
    """
    Generate a unique cache key for a search query

    Args:
        query: Search query string
        filters: Parsed filters dict
        geo_config: Geo configuration dict
        include_availability: If True, include availability params in cache key.
                             Use True when caching availability-filtered results.

    Returns:
        str: MD5 hash of the search parameters
    """
    # Create a stable string representation of the search parameters
    # Exclude offset/perPage since we cache all results
    cache_params = {
        'query': query,
        'cuisines': sorted(filters.get('cuisines', [])),
        'price_ranges': sorted(filters.get('price_ranges', [])),
        'geo': str(sorted(geo_config.items()))
    }

    # When caching availability-filtered results, include availability params in the key
    # so different dates/party sizes get separate cache entries
    if include_availability:
        cache_params['available_only'] = filters.get('available_only', False)
        cache_params['not_released_only'] = filters.get('not_released_only', False)
        cache_params['available_day'] = filters.get('available_day', '')
        cache_params['available_party_size'] = filters.get('available_party_size', 2)
        cache_params['desired_time'] = filters.get('desired_time', '')

    cache_str = json.dumps(cache_params, sort_keys=True)
    return md5(cache_str.encode()).hexdigest()


def get_cached_search_results(cache_key):
    """
    Get cached search results if available and not expired

    Args:
        cache_key: Cache key string

    Returns:
        dict or None: Cached results if valid, None otherwise
    """
    if cache_key not in SEARCH_CACHE:
        return None

    cached = SEARCH_CACHE[cache_key]
    age = time() - cached['timestamp']

    if age > SEARCH_CACHE_TTL:
        # Cache expired, remove it
        del SEARCH_CACHE[cache_key]
        print(f"[CACHE] Cache expired for key {cache_key[:8]}... (age: {age:.1f}s)")
        return None

    print(f"[CACHE] Cache hit for key {cache_key[:8]}... (age: {age:.1f}s, {len(cached['results'])} results)")
    return cached


def save_search_results_to_cache(cache_key, results, total):
    """
    Save search results to cache

    Args:
        cache_key: Cache key string
        results: List of search results
        total: Total count from Resy API
    """
    SEARCH_CACHE[cache_key] = {
        'results': results,
        'total': total,
        'timestamp': time()
    }
    print(f"[CACHE] Saved {len(results)} results to cache (key: {cache_key[:8]}...)")


def parse_search_filters(request_args):
    """
    Parse common search filter parameters from request arguments

    Returns:
        dict: Parsed filters including cuisines, price_ranges, availability params, and pagination
    """
    cuisines_param = request_args.get('cuisines', '').strip()
    price_ranges_param = request_args.get('priceRanges', '').strip()

    # Parse lists
    cuisines = [c.strip() for c in cuisines_param.split(',') if c.strip()] if cuisines_param else []
    price_ranges = (
        [int(p.strip()) for p in price_ranges_param.split(',') if p.strip().isdigit()]
        if price_ranges_param
        else []
    )

    # Parse availability parameters
    available_only = request_args.get('available_only', 'false').lower() == 'true'
    not_released_only = request_args.get('not_released_only', 'false').lower() == 'true'
    available_day = request_args.get('available_day', '').strip()
    available_party_size = int(request_args.get('available_party_size', '2'))
    desired_time = request_args.get('desired_time', '').strip()

    # Parse pagination - use offset instead of page for better filtering
    offset = int(request_args.get('offset', '0'))
    per_page = min(int(request_args.get('perPage', '20')), 50)  # Cap at 50

    return {
        'cuisines': cuisines,
        'price_ranges': price_ranges,
        'available_only': available_only,
        'not_released_only': not_released_only,
        'available_day': available_day,
        'available_party_size': available_party_size,
        'desired_time': desired_time,
        'offset': offset,
        'per_page': per_page
    }


def fetch_until_enough_results(
    search_func, target_count, filters, max_fetches=10,
    config=None, fetch_availability=False, job_id=None
):
    """
    Keep fetching results until we have enough filtered results

    Args:
        search_func: Function that fetches results from Resy API (takes page number)
        target_count: Number of filtered results we want
        filters: Filter criteria
        max_fetches: Maximum number of API calls to make
        config: ResyConfig object (optional, needed for availability fetching)
        fetch_availability: Whether to fetch available times for each venue
        job_id: Optional job ID for Firestore progress updates

    Returns:
        tuple: (results list, total_fetched, has_more)
    """
    all_results = []
    seen_ids = set()
    resy_page = 1
    total_resy_results = 0
    hits = []  # Initialize for has_more check

    # If target_count is 0, return immediately
    if target_count == 0:
        return [], 0, False

    for _ in range(max_fetches):
        print(f"[FETCH] Fetching Resy page {resy_page} (have {len(all_results)}/{target_count} filtered results)")

        # Fetch from Resy API
        hits, resy_total = search_func(resy_page)

        if not hits:
            print("[FETCH] No more results from Resy API")
            break

        # Filter and format
        page_results, filtered_count, seen_ids = filter_and_format_venues(
            hits, filters, seen_ids, config=config, fetch_availability=fetch_availability
        )
        all_results.extend(page_results)
        total_resy_results = resy_total

        log_msg = f"Page {resy_page}: {len(hits)} hits, {len(page_results)} passed filters, {len(all_results)} total"
        print(f"[FETCH] {log_msg}")
        print(f"[FETCH] Filtered counts: {filtered_count}")

        # Update Firestore progress
        if job_id:
            update_search_progress(job_id, {
                "status": "running",
                "stage": "fetching_resy",
                "pagesFetched": resy_page,
                "filteredCount": len(all_results),
                "lastLog": log_msg,
            })

        # Check if we have enough
        if len(all_results) >= target_count:
            break

        # Check if Resy has more results
        if len(hits) < 20:  # Resy returns 20 per page by default
            print("[FETCH] Resy returned fewer than 20 results, no more available")
            break

        resy_page += 1

    # Calculate has_more:
    # - If we got more results than target, definitely more available
    # - If we got exactly 20 hits on the last page, might be more
    # - If we reached max_fetches without getting enough results, assume more might exist
    has_more = (
        len(all_results) > target_count or
        (len(hits) == 20 and resy_page <= max_fetches) or
        (len(all_results) < target_count and resy_page > max_fetches)
    )

    return all_results, total_resy_results, has_more


def build_search_payload(query, filters, geo_config, page=1):
    """
    Build Resy API search payload

    Args:
        query: Search query string
        filters: Dict of parsed filters from parse_search_filters()
        geo_config: Dict with either {'latitude', 'longitude', 'radius'} or
            {'bounding_box': [swLat, swLng, neLat, neLng]}
        page: Resy API page number (default: 1)

    Returns:
        dict: Resy API search payload
    """
    # Build search query - if no name query, search by cuisine, or if no cuisine, leave blank
    search_query = query if query else (filters['cuisines'][0] if filters['cuisines'] else '')

    payload = {
        "availability": filters.get('available_only', False),
        "page": page,
        "per_page": 20,
        "geo": geo_config,
        "highlight": {
            "pre_tag": "<b>",
            "post_tag": "</b>"
        },
        "query": search_query,
        "types": ["venue"],
        "order_by": "availability" if 'latitude' in geo_config else "distance"
    }

    # Add slot_filter if available_only is enabled
    if filters.get('available_only') and filters.get('available_day') and filters.get('available_party_size'):
        payload['slot_filter'] = {
            'day': filters['available_day'],
            'party_size': filters['available_party_size']
        }

    return payload


def is_transient_resy_error(error):
    """Return True if the error looks transient (timeouts/5xx) from Resy."""
    if isinstance(
        error,
        (requests.exceptions.Timeout, requests.exceptions.ReadTimeout,
         requests.exceptions.ConnectionError)
    ):
        return True

    if isinstance(error, requests.exceptions.HTTPError):
        status = getattr(error.response, "status_code", None)
        if status in TRANSIENT_STATUS_CODES:
            return True

    message = str(error).lower()
    if any(code in message for code in [" 500", " 502", "bad gateway", "read timed out"]):
        return True

    return False


def retry_with_backoff(func, max_attempts=3, base_delay=0.3):
    """
    Retry a callable on transient Resy errors with exponential backoff.

    Args:
        func: Callable to execute.
        max_attempts: Total attempts (including the first).
        base_delay: Initial delay in seconds; doubles each retry.
    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if not is_transient_resy_error(exc) or attempt == max_attempts - 1:
                raise

            delay = base_delay * (2 ** attempt)
            time_module.sleep(delay)

    if last_error:
        raise last_error


def _fetch_calendar(headers, params):
    """Wrapper for the calendar GET so we can reuse retry logic."""
    response = requests.get(
        'https://api.resy.com/4/venue/calendar',
        params=params,
        headers=headers,
        timeout=10
    )

    if response.status_code in TRANSIENT_STATUS_CODES:
        raise requests.exceptions.HTTPError(
            f"Calendar returned {response.status_code}",
            response=response
        )

    return response


def get_venue_availability(venue_id, day, party_size, config):
    """
    Fetch available time slots for a specific venue

    Args:
        venue_id: The venue ID
        day: Date in YYYY-MM-DD format
        party_size: Number of people
        config: ResyConfig object or dict

    Returns:
        Dict with 'times' (list of time strings) and 'status' (reason if no times available)
        Example: {'times': ["6:00 PM", "7:00 PM"], 'status': None}
        Example: {'times': [], 'status': 'Closed'}
        Example: {'times': [], 'status': 'Sold out'}
        Example: {'times': [], 'status': 'Not released yet'}
    """
    try:
        # Add a small delay to help with rate limiting (0.1 seconds)
        time_module.sleep(0.1)

        # Store original config for headers (needs dict)
        config_dict = config if isinstance(config, dict) else {
            'api_key': config.api_key,
            'token': config.token,
            'payment_method_id': config.payment_method_id,
            'email': config.email,
            'password': config.password
        }

        # Convert dict config to ResyConfig object if needed
        if isinstance(config, dict):
            config = ResyConfig(**config)

        # First, check the calendar API to determine the status for this specific day
        headers = get_resy_headers(config_dict)

        # Parse the day to get start and end dates for calendar query
        target_date = datetime.strptime(day, '%Y-%m-%d').date()

        params = {
            'venue_id': venue_id,
            'num_seats': int(party_size),
            'start_date': target_date.strftime('%Y-%m-%d'),
            'end_date': target_date.strftime('%Y-%m-%d')
        }

        calendar_response = None
        try:
            calendar_response = retry_with_backoff(
                lambda: _fetch_calendar(headers, params),
                max_attempts=3,
                base_delay=0.3
            )
        except Exception as calendar_error:
            if is_transient_resy_error(calendar_error):
                print(f"[AVAILABILITY] Transient calendar error for venue {venue_id}: {calendar_error}")
            else:
                print(f"[AVAILABILITY] Calendar error for venue {venue_id}: {calendar_error}")

        if calendar_response and calendar_response.status_code == 200:
            calendar_data = calendar_response.json()
            scheduled = calendar_data.get('scheduled', [])

            # Check if the target date is in the scheduled list
            date_found = False
            reservation_status = None

            for entry in scheduled:
                if entry.get('date') == day:
                    date_found = True
                    inventory = entry.get('inventory', {})
                    reservation_status = inventory.get('reservation')
                    break

            # If date is not in scheduled list, it means it hasn't been released yet
            if not date_found:
                print(f"[AVAILABILITY] Date {day} not in calendar for venue {venue_id} - not released yet")
                return {'times': [], 'status': 'Not released yet'}

            # If the status is 'closed', restaurant is closed that day
            if reservation_status == 'closed':
                print(f"[AVAILABILITY] Venue {venue_id} is closed on {day}")
                return {'times': [], 'status': 'Closed'}

            # If the status is 'sold-out' or 'not available', it's sold out
            if reservation_status in ['sold-out', 'not available']:
                print(f"[AVAILABILITY] Venue {venue_id} is sold out on {day}")
                return {'times': [], 'status': 'Sold out'}

        # If we get here, the calendar shows availability or we couldn't check the calendar
        # Try to fetch actual time slots
        api_access = ResyApiAccess.build(config)

        # Create find request
        find_request = FindRequestBody(
            day=day,
            party_size=int(party_size),
            venue_id=str(venue_id)
        )

        # Get slots with retry for transient failures
        try:
            slots = retry_with_backoff(
                lambda: api_access.find_booking_slots(find_request),
                max_attempts=3,
                base_delay=0.3
            )
        except Exception as slot_error:
            # Enhanced error logging
            error_details = {
                'error_type': type(slot_error).__name__,
                'error_message': str(slot_error),
                'error_args': getattr(slot_error, 'args', None),
                'is_transient': is_transient_resy_error(slot_error),
                'venue_id': venue_id,
                'day': day,
                'party_size': party_size,
            }

            # Try to get HTTP status code if it's an HTTPError
            if isinstance(slot_error, requests.exceptions.HTTPError):
                response = getattr(slot_error, 'response', None)
                if response is not None:
                    error_details['http_status'] = response.status_code
                    error_details['http_response'] = getattr(response, 'text', None)

            print(f"[AVAILABILITY] Error fetching slots for venue {venue_id}: {error_details}")
            print(f"[AVAILABILITY] Full traceback:\n{traceback.format_exc()}")

            if is_transient_resy_error(slot_error):
                return {'times': [], 'status': 'Resy temporarily unavailable'}

            return {'times': [], 'status': 'Unable to fetch'}

        if not slots:
            # No slots returned - check if calendar said available but we got no slots
            # This could mean sold out or an error
            print(f"[AVAILABILITY] No slots returned for venue {venue_id} on {day}")
            return {'times': [], 'status': 'Sold out'}

        # Sort slots chronologically for display
        sorted_slots = sorted(slots, key=lambda slot: slot.date.start)

        # If desired_time is provided, we could prioritize those times,
        # but for now we'll just return all slots in chronological order
        # The frontend will handle deduplication of times with different seating types

        # Format the slots into time strings
        available_times = []
        for slot in sorted_slots:
            # Format the time nicely
            time_str = slot.date.start.strftime("%-I:%M %p")
            available_times.append(time_str)

        return {'times': available_times, 'status': None}
    except Exception as e:
        # Enhanced error logging for top-level exception
        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'error_args': getattr(e, 'args', None),
            'venue_id': venue_id,
            'day': day,
            'party_size': party_size,
        }

        # Try to get HTTP status code if it's an HTTPError
        if isinstance(e, requests.exceptions.HTTPError):
            response = getattr(e, 'response', None)
            if response is not None:
                error_details['http_status'] = response.status_code
                error_details['http_response'] = getattr(response, 'text', None)

        print(f"[AVAILABILITY] Top-level error fetching availability for venue {venue_id}: {error_details}")
        print(f"[AVAILABILITY] Full traceback:\n{traceback.format_exc()}")
        return {'times': [], 'status': 'Unable to fetch'}


def filter_and_format_venues(hits, filters, seen_ids=None, config=None, fetch_availability=False):
    """
    Apply client-side filters and format venue results

    Args:
        hits: List of venue hits from Resy API
        filters: Dict of parsed filters from parse_search_filters()
        seen_ids: Set of venue IDs we've already processed (to avoid duplicates)
        config: ResyConfig object (required if fetch_availability is True)
        fetch_availability: Whether to fetch available time slots for each venue

    Returns:
        tuple: (results list, filtered_count dict, seen_ids set)
    """
    results = []
    filtered_count = {'cuisine': 0, 'price': 0, 'duplicate': 0, 'availability': 0}
    if seen_ids is None:
        seen_ids = set()

    for hit in hits:
        venue = hit.get('_source') or hit

        if not venue or not venue.get('name'):
            continue

        # Get venue ID
        venue_id = venue.get('id', {}).get('resy') if isinstance(venue.get('id'), dict) else venue.get('id')

        # Skip duplicates
        if venue_id in seen_ids:
            filtered_count['duplicate'] += 1
            continue

        seen_ids.add(venue_id)

        # Apply cuisine filter - check both 'type' field and search if type is empty
        venue_cuisine = venue.get('cuisine', [])[0] if venue.get('cuisine') else ""
        if filters['cuisines'] and venue_cuisine:  # Only filter if venue_cuisine is not empty
            if not any(cuisine.lower() in venue_cuisine.lower() for cuisine in filters['cuisines']):
                filtered_count['cuisine'] += 1
                continue

        # Apply price range filter
        venue_price = venue.get('price_range_id') or venue.get('price_range', 0)
        if filters['price_ranges'] and venue_price not in filters['price_ranges']:
            filtered_count['price'] += 1
            continue

        neighborhood = venue.get('neighborhood', {})
        geoloc = venue.get('_geoloc', {})

        venue_name = venue.get('name', 'Unknown')

        # Get image URL directly from Resy API
        resy_image_url = venue.get('images')[0] if venue.get('images') else None

        result = {
            'id': venue_id or 'unknown',
            'name': venue_name,
            'locality': venue.get('locality', 'N/A'),
            'region': venue.get('region', 'N/A'),
            'type': venue_cuisine,
            'price_range': venue_price,
            'latitude': geoloc.get('lat'),
            'longitude': geoloc.get('lng'),
            'imageUrl': resy_image_url,
            'neighborhood': neighborhood
        }

        # Fetch availability if requested
        if fetch_availability and config and filters.get('available_day') and filters.get('available_party_size'):
            availability_data = get_venue_availability(
                venue_id,
                filters['available_day'],
                filters['available_party_size'],
                config
            )
            # availability_data is a dict with 'times' and 'status'
            if availability_data['times']:
                result['availableTimes'] = availability_data['times']
            elif availability_data['status']:
                result['availabilityStatus'] = availability_data['status']

            # If available_only filter is enabled, skip venues without available times
            if filters.get('available_only') and not availability_data['times']:
                filtered_count['availability'] = filtered_count.get('availability', 0) + 1
                continue

            # If not_released_only filter is enabled, skip venues that are not "Not released yet"
            if filters.get('not_released_only'):
                if availability_data['status'] != 'Not released yet':
                    filtered_count['not_released'] = filtered_count.get('not_released', 0) + 1
                    continue

        results.append(result)

    return results, filtered_count, seen_ids
