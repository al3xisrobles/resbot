"""
Shared utility functions for Resy Bot Cloud Functions
Includes credential loading, photo caching, search caching, and Resy API helpers
"""

import os
import json
import logging
import requests
from time import time
from hashlib import md5
from google import genai
from firebase_admin import storage, firestore

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

# Search results cache with TTL (5 minutes)
# Format: {cache_key: {'results': [...], 'total': int, 'timestamp': float}}
SEARCH_CACHE = {}
SEARCH_CACHE_TTL = 300  # 5 minutes in seconds

# In-memory cache for venue photos
photo_cache = {}

# Initialize Gemini AI client if API key is available
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Firebase Storage bucket (lazily initialized)
_firebase_bucket = None

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

def get_firebase_bucket():
    """Lazily get Firebase Storage bucket"""
    global _firebase_bucket
    if _firebase_bucket is None:
        try:
            _firebase_bucket = storage.bucket()
            logger.info("✓ Firebase Storage initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to get Firebase bucket: {str(e)}")
            _firebase_bucket = None
    return _firebase_bucket


def fetch_venue_photo_with_cache(venue_id, restaurant_name):
    """
    Fetch venue photo with three-layer caching

    Args:
        venue_id: Resy venue ID
        restaurant_name: Name of the restaurant

    Returns:
        str: Photo URL if found, None otherwise
    """
    if not GOOGLE_MAPS_API_KEY:
        return None

    # Create cache key from venue_id and restaurant_name
    cache_key = f"{venue_id}_{restaurant_name}"

    # 1. Check in-memory cache first (fastest)
    if cache_key in photo_cache:
        logger.info(f"✓ [{restaurant_name}] CACHE HIT - Memory")
        return photo_cache[cache_key].get('photoUrl')

    # 2. Check Firebase Storage cache (fast)
    firebase_bucket = get_firebase_bucket()
    if firebase_bucket:
        try:
            blob_name = f"venue_photos/{venue_id}.json"
            blob = firebase_bucket.blob(blob_name)

            if blob.exists():
                cached_data = json.loads(blob.download_as_text())
                logger.info(f"✓ [{restaurant_name}] CACHE HIT - Firebase | Saved to memory")

                # Store in memory cache for next time
                photo_cache[cache_key] = cached_data

                return cached_data.get('photoUrl')
        except Exception as e:
            logger.warning(f"✗ [{restaurant_name}] Firebase cache read failed: {str(e)}")

    # 3. CACHE MISS - Fetch from Google Places API (expensive!)
    try:
        logger.info(f"→ [{restaurant_name}] Fetching from Google Places API...")

        # Use Text Search API to find the restaurant
        search_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        search_params = {
            'query': f"{restaurant_name} restaurant New York",
            'key': GOOGLE_MAPS_API_KEY
        }

        search_response = requests.get(search_url, params=search_params, timeout=10)

        if search_response.status_code != 200:
            logger.error(f"✗ [{restaurant_name}] Google Places API error {search_response.status_code}")
            return None

        search_data = search_response.json()

        # Check if we got results
        if not search_data.get('results') or len(search_data['results']) == 0:
            logger.warning(f"✗ [{restaurant_name}] No Google Places results")
            return None

        # Get the first result
        place = search_data['results'][0]
        photos = place.get('photos', [])

        if not photos or len(photos) == 0:
            logger.warning(f"✗ [{restaurant_name}] No photos available")
            return None

        # Get just ONE photo (reduce costs)
        photo = photos[0]
        photo_reference = photo.get('photo_reference')

        if not photo_reference:
            logger.warning(f"✗ [{restaurant_name}] No photo reference")
            return None

        # Construct photo URL (maxwidth=800 for cost savings)
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"

        # Build cache data
        result_data = {
            'photoUrls': [photo_url],
            'photoUrl': photo_url,
            'placeName': place.get('name'),
            'placeAddress': place.get('formatted_address', 'N/A')
        }

        # Store in in-memory cache
        photo_cache[cache_key] = result_data
        logger.info(f"✓ [{restaurant_name}] SAVED - Memory cache")

        # Store in Firebase Storage cache (if available)
        if firebase_bucket:
            try:
                blob_name = f"venue_photos/{venue_id}.json"
                blob = firebase_bucket.blob(blob_name)
                blob.upload_from_string(
                    json.dumps(result_data),
                    content_type='application/json'
                )
                logger.info(f"✓ [{restaurant_name}] SAVED - Firebase Storage (blob: {blob_name})")
            except Exception as e:
                logger.warning(f"✗ [{restaurant_name}] Firebase save failed: {str(e)}")
        else:
            logger.info(f"⚠ [{restaurant_name}] Firebase not available - memory cache only")

        logger.info(f"✓ [{restaurant_name}] IMAGE SOURCE - Google Places API")
        return photo_url

    except Exception as e:
        logger.error(f"✗ [{restaurant_name}] Error fetching from Google Places: {str(e)}")
        return None


def fetch_venue_image_for_list(venue_id, venue_name, image_data):
    """
    Fetch venue image for list endpoints with detailed logging
    Tries: 1) Memory cache, 2) Firebase cache, 3) Resy API, 4) Google Places API

    Args:
        venue_id: Resy venue ID
        venue_name: Restaurant name
        image_data: responsive_images data from Resy API

    Returns:
        str: Image URL if found, None otherwise
    """
    cache_key = f"{venue_id}_{venue_name}"
    logger.info(f"📸 [{venue_name}] Starting photo lookup (venue_id={venue_id})")

    # 1. Check in-memory cache
    if cache_key in photo_cache:
        image_url = photo_cache[cache_key].get('photoUrl')
        logger.info(f"✓ [{venue_name}] CACHE HIT - Memory")
        return image_url

    # 2. Check Firebase cache
    firebase_bucket = get_firebase_bucket()
    if firebase_bucket:
        try:
            blob_name = f"venue_photos/{venue_id}.json"
            blob = firebase_bucket.blob(blob_name)
            if blob.exists():
                cached_data = json.loads(blob.download_as_text())
                image_url = cached_data.get('photoUrl')
                photo_cache[cache_key] = cached_data
                logger.info(f"✓ [{venue_name}] CACHE HIT - Firebase | Saved to memory")
                return image_url
            else:
                logger.info(f"✗ [{venue_name}] Not in Firebase cache")
        except Exception as e:
            logger.warning(f"✗ [{venue_name}] Firebase cache read failed: {str(e)}")

    # 3. Check Resy API for image
    urls = image_data.get('urls', {})
    if urls:
        first_file = image_data.get('file_names', [None])[0]
        if first_file and first_file in urls:
            aspect_ratios = urls[first_file]
            if '1:1' in aspect_ratios and '400' in aspect_ratios['1:1']:
                image_url = aspect_ratios['1:1']['400']
                logger.info(f"✓ [{venue_name}] IMAGE SOURCE - Resy API")

                # Cache the Resy image
                result_data = {
                    'photoUrls': [image_url],
                    'photoUrl': image_url,
                    'placeName': venue_name,
                    'placeAddress': 'N/A'
                }

                photo_cache[cache_key] = result_data
                logger.info(f"✓ [{venue_name}] SAVED - Memory cache")

                if firebase_bucket:
                    try:
                        blob = firebase_bucket.blob(f"venue_photos/{venue_id}.json")
                        blob.upload_from_string(json.dumps(result_data), content_type='application/json')
                        logger.info(f"✓ [{venue_name}] SAVED - Firebase Storage (blob: venue_photos/{venue_id}.json)")
                    except Exception as e:
                        logger.warning(f"✗ [{venue_name}] Firebase save failed: {str(e)}")
                else:
                    logger.info(f"⚠ [{venue_name}] Firebase not available - memory cache only")

                return image_url

    logger.info(f"✗ [{venue_name}] No image in Resy API response")

    # 4. Fetch from Google Places as last resort
    if venue_id and venue_name and GOOGLE_MAPS_API_KEY:
        return fetch_venue_photo_with_cache(venue_id, venue_name)

    logger.warning(f"✗ [{venue_name}] NO IMAGE FOUND from any source")
    return None


def load_credentials(userId=None):
    """
    Load Resy credentials from Firestore

    Args:
        user_id: Firebase user ID. Required.

    Returns:
        dict: Credentials containing api_key, token, etc.

    Note:
        The Firestore document uses camelCase field names (apiKey, paymentMethodId)
        but this function returns snake_case for backwards compatibility
    """
    if not userId:
        logger.error("✗ userId not provided for loading credentials from Firestore")
        raise ValueError("userId is required to load credentials from Firestore")

    try:
        db = firestore.client()
        doc = db.collection('resyCredentials').document(userId).get()

        if not doc.exists:
            logger.warning(f"✗ No Resy credentials found in Firestore for user {userId}")
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

        logger.info(f"✓ Loaded Resy credentials from Firestore for user {userId}")
        return credentials

    except Exception as e:
        logger.error(f"✗ Error loading credentials from Firestore: {str(e)}")
        raise


def get_resy_headers(config):
    """Build Resy API headers"""
    return {
        'Authorization': f'ResyAPI api_key="{config["api_key"]}"',
        'X-Resy-Auth-Token': config['token'],
        'X-Resy-Universal-Auth': config['token'],
        'Origin': 'https://resy.com',
        'X-origin': 'https://resy.com',
        'Referer': 'https://resy.com/',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }


def get_search_cache_key(query, filters, geo_config):
    """
    Generate a unique cache key for a search query

    Args:
        query: Search query string
        filters: Parsed filters dict
        geo_config: Geo configuration dict

    Returns:
        str: MD5 hash of the search parameters
    """
    # Create a stable string representation of the search parameters
    # Exclude offset/perPage since we cache all results
    cache_params = {
        'query': query,
        'cuisines': sorted(filters.get('cuisines', [])),
        'price_ranges': sorted(filters.get('price_ranges', [])),
        'available_only': filters.get('available_only', False),
        'available_day': filters.get('available_day', ''),
        'available_party_size': filters.get('available_party_size', 2),
        'desired_time': filters.get('desired_time', ''),
        'geo': str(sorted(geo_config.items()))
    }
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
    price_ranges = [int(p.strip()) for p in price_ranges_param.split(',') if p.strip().isdigit()] if price_ranges_param else []

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


def fetch_until_enough_results(search_func, target_count, filters, max_fetches=10, config=None, fetch_availability=False):
    """
    Keep fetching results until we have enough filtered results

    Args:
        search_func: Function that fetches results from Resy API (takes page number)
        target_count: Number of filtered results we want
        filters: Filter criteria
        max_fetches: Maximum number of API calls to make
        config: ResyConfig object (optional, needed for availability fetching)
        fetch_availability: Whether to fetch available times for each venue

    Returns:
        tuple: (results list, total_fetched, has_more)
    """
    all_results = []
    seen_ids = set()
    resy_page = 1
    total_resy_results = 0

    for _ in range(max_fetches):
        print(f"[FETCH] Fetching Resy page {resy_page} (have {len(all_results)}/{target_count} filtered results)")

        # Fetch from Resy API
        hits, resy_total = search_func(resy_page)

        if not hits:
            print(f"[FETCH] No more results from Resy API")
            break

        # Filter and format
        page_results, filtered_count, seen_ids = filter_and_format_venues(
            hits, filters, seen_ids, config=config, fetch_availability=fetch_availability
        )
        all_results.extend(page_results)
        total_resy_results = resy_total

        print(f"[FETCH] Page {resy_page}: got {len(hits)} hits, {len(page_results)} passed filters, {len(all_results)} total")
        print(f"[FETCH] Filtered counts: {filtered_count}")

        # Check if we have enough
        if len(all_results) >= target_count:
            break

        # Check if Resy has more results
        if len(hits) < 20:  # Resy returns 20 per page by default
            print(f"[FETCH] Resy returned fewer than 20 results, no more available")
            break

        resy_page += 1

    has_more = len(all_results) > target_count or (len(hits) == 20 and resy_page <= max_fetches)

    return all_results, total_resy_results, has_more


def build_search_payload(query, filters, geo_config, page=1):
    """
    Build Resy API search payload

    Args:
        query: Search query string
        filters: Dict of parsed filters from parse_search_filters()
        geo_config: Dict with either {'latitude', 'longitude', 'radius'} or {'bounding_box': [swLat, swLng, neLat, neLng]}
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


def get_venue_availability(venue_id, day, party_size, config, desired_time=None):
    """
    Fetch available time slots for a specific venue

    Args:
        venue_id: The venue ID
        day: Date in YYYY-MM-DD format
        party_size: Number of people
        config: ResyConfig object or dict
        desired_time: Optional desired time in HH:MM format (24-hour) to sort by proximity

    Returns:
        Dict with 'times' (list of time strings) and 'status' (reason if no times available)
        Example: {'times': ["6:00 PM", "7:00 PM"], 'status': None}
        Example: {'times': [], 'status': 'Closed'}
        Example: {'times': [], 'status': 'Sold out'}
        Example: {'times': [], 'status': 'Not released yet'}
    """
    try:
        from resy_client.models import FindRequestBody, ResyConfig
        from resy_client.api_access import ResyApiAccess
        from datetime import datetime
        import time as time_module

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

        calendar_response = requests.get(
            'https://api.resy.com/4/venue/calendar',
            params=params,
            headers=headers,
            timeout=10
        )

        if calendar_response.status_code == 200:
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

        # Get slots
        slots = api_access.find_booking_slots(find_request)

        if not slots:
            # No slots returned - check if calendar said available but we got no slots
            # This could mean sold out or an error
            print(f"[AVAILABILITY] No slots returned for venue {venue_id} on {day}")
            return {'times': [], 'status': 'Sold out'}

        # If desired_time is provided, sort by proximity to desired time
        if desired_time:
            try:
                # Parse desired time (format: "19:00")
                desired_hour, desired_minute = map(int, desired_time.split(':'))
                desired_minutes_from_midnight = desired_hour * 60 + desired_minute

                # Sort slots by proximity to desired time
                def time_distance(slot):
                    slot_time = slot.date.start
                    slot_minutes = slot_time.hour * 60 + slot_time.minute
                    return abs(slot_minutes - desired_minutes_from_midnight)

                sorted_slots = sorted(slots, key=time_distance)
            except Exception as e:
                print(f"[AVAILABILITY] Error sorting by desired time: {str(e)}")
                sorted_slots = slots
        else:
            sorted_slots = slots

        # Get the 8 closest slots
        closest_slots = sorted_slots[:8]

        # Sort them chronologically for display
        closest_slots.sort(key=lambda slot: slot.date.start)

        # Format the slots into time strings
        available_times = []
        for slot in closest_slots:
            # Format the time nicely
            time_str = slot.date.start.strftime("%-I:%M %p")
            available_times.append(time_str)

        return {'times': available_times, 'status': None}
    except Exception as e:
        # If there's any error fetching availability, return error status
        print(f"[AVAILABILITY] Error fetching availability for venue {venue_id}: {str(e)}")
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
        venue_type = venue.get('type', '')
        if filters['cuisines'] and venue_type:  # Only filter if type is not empty
            if not any(cuisine.lower() in venue_type.lower() for cuisine in filters['cuisines']):
                filtered_count['cuisine'] += 1
                continue

        # Apply price range filter
        venue_price = venue.get('price_range_id') or venue.get('price_range', 0)
        if filters['price_ranges'] and venue_price not in filters['price_ranges']:
            filtered_count['price'] += 1
            continue

        location = venue.get('location', {})
        geoloc = venue.get('_geoloc', {})

        # Construct photo proxy URL for lazy loading
        from urllib.parse import quote
        venue_name = venue.get('name', 'Unknown')
        image_url = f"{CLOUD_FUNCTIONS_BASE}/venue_photo_proxy?id={venue_id}&name={quote(venue_name)}"

        result = {
            'id': venue_id or 'unknown',
            'name': venue_name,
            'locality': venue.get('locality', 'N/A'),
            'region': venue.get('region', 'N/A'),
            'type': venue.get('type', 'N/A'),
            'price_range': venue_price,
            'address': f"{location.get('address_1', '')}, {venue.get('locality', '')}, {venue.get('region', '')}" if location.get('address_1') else None,
            'latitude': geoloc.get('lat'),
            'longitude': geoloc.get('lng'),
            'imageUrl': image_url,
            'neighborhood': location.get('neighborhood', 'N/A')
        }

        # Fetch availability if requested
        if fetch_availability and config and filters.get('available_day') and filters.get('available_party_size'):
            availability_data = get_venue_availability(
                venue_id,
                filters['available_day'],
                filters['available_party_size'],
                config,
                filters.get('desired_time')
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
