"""
Venue-related Cloud Functions for Resy Bot
Handles venue details and links
"""

import logging
import requests

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption

from .sentry_utils import with_sentry_trace
from .utils import (
    load_credentials,
    get_resy_headers,
    GOOGLE_MAPS_API_KEY
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]), timeout_sec=60, memory=MemoryOption.GB_1)
@with_sentry_trace
def venue(req: Request):
    """
    GET /venue?id=<venue_id>&userId=<user_id>
    Get restaurant information by venue ID with cached photo
    Query parameters:
    - id: Venue ID (required)
    - userId: Optional Firebase user ID for personalized credentials
    """
    try:
        venue_id = req.args.get('id')
        user_id = req.args.get('userId')

        if not venue_id:
            return {
                'success': False,
                'error': 'Missing venue_id parameter'
            }, 400

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        response = requests.get(
            'https://api.resy.com/3/venue',
            params={'id': venue_id},
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        venue_data = response.json()
        venue_name = venue_data.get('name')

        # Get photo URLs directly from Resy API
        photo_urls = venue_data.get('images', [])

        # Get description from metadata
        metadata = venue_data.get('metadata', {})
        description = metadata.get('description', '')

        return {
            'success': True,
            'data': {
                'name': venue_name,
                'venue_id': venue_id,
                'type': venue_data.get('type', 'N/A'),
                'address': (
                    f"{venue_data.get('location', {}).get('address_1', '')}, "
                    f"{venue_data.get('location', {}).get('locality', '')}, "
                    f"{venue_data.get('location', {}).get('region', '')}"
                    if venue_data.get('location')
                    else 'N/A'
                ),
                'neighborhood': venue_data.get('location', {}).get('neighborhood', ''),
                'price_range': venue_data.get('price_range_id', 0),
                'rating': venue_data.get('rater', [])[0].get('score') if venue_data.get('rater') else None,
                'photoUrls': photo_urls,  # List of photo URLs from Resy
                'description': description,  # Description from metadata
            }
        }

    except Exception as e:
        logger.error("Error fetching venue: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]), timeout_sec=60, memory=MemoryOption.GB_1)
@with_sentry_trace
def venue_links(req: Request):
    """
    GET /venue_links?id=<venue_id>&userId=<user_id>
    Search for restaurant links (Google Maps, Resy)
    Query parameters:
    - id: Venue ID (required)
    - userId: Optional Firebase user ID for personalized credentials
    """
    try:
        venue_id = req.args.get('id')
        user_id = req.args.get('userId')

        if not venue_id:
            return {
                'success': False,
                'error': 'Missing venue_id parameter'
            }, 400

        logger.info("[VENUE-LINKS] Starting link search for venue_id: %s", venue_id)

        # First get venue details to get the restaurant name
        logger.info("[VENUE-LINKS] Fetching venue details from Resy API...")
        credentials = load_credentials(user_id)
        headers = get_resy_headers(credentials)

        # Use the /3/venue endpoint which returns complete venue data
        venue_response = requests.get(
            'https://api.resy.com/3/venue',
            params={'id': venue_id},
            headers=headers,
            timeout=30
        )

        if venue_response.status_code != 200:
            logger.error(
                "[VENUE-LINKS] Failed to fetch venue details. Status: %s",
                venue_response.status_code
            )
            return {
                'success': False,
                'error': 'Failed to fetch venue details'
            }, 500

        venue_data = venue_response.json()
        restaurant_name = venue_data.get('name', '')
        location = venue_data.get('location', {})
        city = location.get('locality', '')

        logger.info("[VENUE-LINKS] Found restaurant: '%s' in %s", restaurant_name, city)

        if not restaurant_name:
            logger.error("[VENUE-LINKS] Restaurant name not found in venue data")
            return {
                'success': False,
                'error': 'Restaurant name not found'
            }, 404

        # Initialize links
        # Clean restaurant name for Resy URL: remove neighborhood suffix (e.g., " - Little Italy", " - New York")
        clean_name = restaurant_name
        if ' - ' in clean_name:
            # Split on ' - ' and take only the first part (restaurant name without neighborhood)
            clean_name = clean_name.split(' - ')[0]

        # Convert to Resy URL format: lowercase, spaces to hyphens, & to "and"
        resy_slug = clean_name.lower().replace(" ", "-").replace("&", "and")
        resy_link = f'https://resy.com/cities/ny/{resy_slug}'
        logger.info(
            "[VENUE-LINKS] Generated Resy link from '%s' -> '%s' -> %s",
            restaurant_name, clean_name, resy_link
        )

        links = {
            'googleMaps': None,
            'resy': resy_link
        }

        # Use Google Places API for Google Maps link
        if GOOGLE_MAPS_API_KEY:
            try:
                logger.info("[VENUE-LINKS] Searching for Google Maps URL using Places API (New)...")

                address_1 = location.get("address_1", "")
                postal_code = location.get("postal_code", "")
                state = location.get("region", "")
                city = location.get("locality", "")

                address_parts = [restaurant_name]
                if address_1:
                    address_parts.append(address_1)
                if city:
                    address_parts.append(city)
                if state:
                    address_parts.append(state)
                if postal_code:
                    address_parts.append(postal_code)

                full_address = ", ".join(address_parts) + " restaurant"

                logger.info("[VENUE-LINKS] Full address data: %s", location)
                logger.info("[VENUE-LINKS] Searching for (Text Search New): %s", full_address)

                places_url = "https://places.googleapis.com/v1/places:searchText"

                # New Places API (New) style: POST + JSON + field mask header
                payload = {
                    "textQuery": full_address,
                }

                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                    # Ask specifically for the maps link so response is small
                    "X-Goog-FieldMask": "places.displayName,places.googleMapsLinks.placeUri",
                }

                places_response = requests.post(
                    places_url, json=payload, headers=headers, timeout=30
                )
                logger.info(
                    "[VENUE-LINKS] Places API (New) status=%s, body=%s",
                    places_response.status_code,
                    places_response.text[:300]
                )

                if places_response.status_code == 200:
                    places_data = places_response.json()

                    places = places_data.get("places", [])
                    if places:
                        first = places[0]
                        links_obj = first.get("googleMapsLinks", {})
                        place_uri = links_obj.get("placeUri")

                        if place_uri:
                            links["googleMaps"] = place_uri
                            logger.info(
                                f"[VENUE-LINKS] ✓ Found Google Maps URL via Places API (New): {links['googleMaps']}"
                            )
                        else:
                            logger.warning(
                                "[VENUE-LINKS] ✗ No googleMapsLinks.placeUri in response"
                            )
                    else:
                        logger.warning("[VENUE-LINKS] ✗ No places returned from Places API (New)")
                else:
                    logger.error(
                        f"[VENUE-LINKS] ✗ Places API (New) request failed. "
                        f"Status: {places_response.status_code}, body={places_response.text[:300]}"
                    )

            except Exception as e:
                logger.error(
                    "[VENUE-LINKS] Error searching Google Maps with Places API (New): %s", e
                )
        else:
            logger.warning(
                "[VENUE-LINKS] Google Places API key not configured, "
                "skipping Google Maps search"
            )

        # Log final results
        found_count = sum(1 for link in links.values() if link is not None)
        logger.info(
            "[VENUE-LINKS] ✓ Completed. Found %s/2 links for '%s'",
            found_count, restaurant_name
        )

        # Debug: Log what we're getting from the API
        logger.info("[VENUE-LINKS] Venue type: %s", venue_data.get('type'))
        logger.info("[VENUE-LINKS] Location address_1: %s", location.get('address_1'))
        logger.info("[VENUE-LINKS] Location neighborhood: %s", location.get('neighborhood'))
        logger.info("[VENUE-LINKS] Price range ID: %s", venue_data.get('price_range_id'))
        logger.info("[VENUE-LINKS] Rating: %s", venue_data.get('rating'))

        response_data = {
            'success': True,
            'links': links,
            'venueData': {
                'name': restaurant_name,
                'type': venue_data.get('type', ''),
                'address': location.get('address_1', ''),
                'neighborhood': location.get('neighborhood', ''),
                'priceRange': venue_data.get('price_range_id', 0),
                'rating': venue_data.get('rating', 0)
            }
        }

        return response_data

    except Exception as e:
        logger.error("[VENUE-LINKS] ✗ Error getting venue links: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500
