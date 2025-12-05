"""
Venue-related Cloud Functions for Resy Bot
Handles venue details, links, and photos
"""

import logging
import requests

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from .utils import (
    load_credentials,
    get_resy_headers,
    fetch_venue_photo_with_cache,
    photo_cache,
    GOOGLE_MAPS_API_KEY
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
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
            headers=headers
        )

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        venue_data = response.json()
        venue_name = venue_data.get('name')

        # Fetch photo with caching
        photo_url = fetch_venue_photo_with_cache(venue_id, venue_name) if venue_name else None

        return {
            'success': True,
            'data': {
                'name': venue_name,
                'venue_id': venue_id,
                'type': venue_data.get('type', 'N/A'),
                'address': f"{venue_data.get('location', {}).get('address_1', '')}, {venue_data.get('location', {}).get('locality', '')}, {venue_data.get('location', {}).get('region', '')}" if venue_data.get('location') else 'N/A',
                'price_range': venue_data.get('price_range_id', 0),
                'rating': venue_data.get('rating'),
                'photoUrl': photo_url
            }
        }

    except Exception as e:
        logger.error(f"Error fetching venue: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
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

        logger.info(f"[VENUE-LINKS] Starting link search for venue_id: {venue_id}")

        # First get venue details to get the restaurant name
        logger.info(f"[VENUE-LINKS] Fetching venue details from Resy API...")
        credentials = load_credentials(user_id)
        headers = get_resy_headers(credentials)

        # Use the /3/venue endpoint which returns complete venue data
        venue_response = requests.get(
            'https://api.resy.com/3/venue',
            params={'id': venue_id},
            headers=headers
        )

        if venue_response.status_code != 200:
            logger.error(f"[VENUE-LINKS] Failed to fetch venue details. Status: {venue_response.status_code}")
            return {
                'success': False,
                'error': 'Failed to fetch venue details'
            }, 500

        venue_data = venue_response.json()
        restaurant_name = venue_data.get('name', '')
        location = venue_data.get('location', {})
        city = location.get('locality', '')

        logger.info(f"[VENUE-LINKS] Found restaurant: '{restaurant_name}' in {city}")

        if not restaurant_name:
            logger.error(f"[VENUE-LINKS] Restaurant name not found in venue data")
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
        logger.info(f"[VENUE-LINKS] Generated Resy link from '{restaurant_name}' -> '{clean_name}' -> {resy_link}")

        links = {
            'googleMaps': None,
            'resy': resy_link
        }

        # Use Google Places API for Google Maps link
        if GOOGLE_MAPS_API_KEY:
            try:
                # Google Maps search using Places API
                logger.info(f"[VENUE-LINKS] Searching for Google Maps URL using Places API...")

                # Get detailed address from venue data
                address_1 = location.get('address_1', '')
                address_2 = location.get('address_2', '')
                neighborhood = location.get('neighborhood', '')
                postal_code = location.get('postal_code', '')
                state = location.get('region', '')

                # Build the most complete address possible
                # Include street address, neighborhood, city, state, zip for best results
                address_parts = [restaurant_name]
                if address_1:
                    address_parts.append(address_1)
                if city:
                    address_parts.append(city)
                if state:
                    address_parts.append(state)
                if postal_code:
                    address_parts.append(postal_code)

                # For type constraint, add "restaurant" to avoid matching law firms, etc.
                full_address = ', '.join(address_parts) + ' restaurant'

                logger.info(f"[VENUE-LINKS] Full address data: {location}")
                logger.info(f"[VENUE-LINKS] Searching for: {full_address}")

                # Use Places API Text Search
                places_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                params = {
                    'input': full_address,
                    'inputtype': 'textquery',
                    'fields': 'place_id,name',
                    'key': GOOGLE_MAPS_API_KEY
                }

                places_response = requests.get(places_url, params=params)

                if places_response.status_code == 200:
                    places_data = places_response.json()

                    if places_data.get('status') == 'OK' and places_data.get('candidates'):
                        place_id = places_data['candidates'][0]['place_id']
                        # Construct Google Maps URL
                        links['googleMaps'] = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                        logger.info(f"[VENUE-LINKS] ✓ Found Google Maps URL via Places API: {links['googleMaps']}")
                    else:
                        logger.warning(f"[VENUE-LINKS] ✗ No results from Places API. Status: {places_data.get('status')}")
                else:
                    logger.error(f"[VENUE-LINKS] ✗ Places API request failed. Status: {places_response.status_code}")

            except Exception as e:
                logger.error(f"[VENUE-LINKS] Error searching Google Maps with Places API: {str(e)}")
        else:
            logger.warning(f"[VENUE-LINKS] Google Places API key not configured, skipping Google Maps search")

        # Log final results
        found_count = sum(1 for link in links.values() if link is not None)
        logger.info(f"[VENUE-LINKS] ✓ Completed. Found {found_count}/2 links for '{restaurant_name}'")

        # Debug: Log what we're getting from the API
        logger.info(f"[VENUE-LINKS] Venue type: {venue_data.get('type')}")
        logger.info(f"[VENUE-LINKS] Location address_1: {location.get('address_1')}")
        logger.info(f"[VENUE-LINKS] Location neighborhood: {location.get('neighborhood')}")
        logger.info(f"[VENUE-LINKS] Price range ID: {venue_data.get('price_range_id')}")
        logger.info(f"[VENUE-LINKS] Rating: {venue_data.get('rating')}")

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
        logger.error(f"[VENUE-LINKS] ✗ Error getting venue links: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def venue_photo(req: Request):
    """
    GET /venue_photo?id=<venue_id>&name=<restaurant_name>
    Get Google Places photo URL for a restaurant with multi-layer caching
    """
    try:
        venue_id = req.args.get('id')
        restaurant_name = req.args.get('name')

        logger.info(f"[PHOTO] Request for venue_id={venue_id}, name={restaurant_name}")

        if not venue_id:
            return {
                'success': False,
                'error': 'Missing venue_id parameter'
            }, 400

        if not restaurant_name:
            logger.warning(f"[PHOTO] Missing restaurant name for venue_id={venue_id}")
            return {
                'success': False,
                'error': 'Missing restaurant name'
            }, 400

        # Fetch photo with caching
        photo_url = fetch_venue_photo_with_cache(venue_id, restaurant_name)
        logger.info(f"[PHOTO] Fetched photo_url={photo_url} for {restaurant_name}")

        if not photo_url:
            logger.warning(f"[PHOTO] No photo available for {restaurant_name} (venue_id={venue_id})")
            return {
                'success': False,
                'error': 'No photo available for this restaurant'
            }, 404

        # Get full metadata from cache
        cache_key = f"{venue_id}_{restaurant_name}"
        cached_data = photo_cache.get(cache_key, {
            'photoUrls': [photo_url],
            'photoUrl': photo_url,
            'placeName': restaurant_name,
            'placeAddress': 'N/A'
        })

        logger.info(f"[PHOTO] Returning data for {restaurant_name}: photoUrl={cached_data.get('photoUrl', 'N/A')}")

        return {
            'success': True,
            'data': cached_data
        }

    except Exception as e:
        logger.error(f"[PHOTO] Error fetching venue photo for venue_id={req.args.get('id')}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def venue_photo_proxy(req: Request):
    """
    GET /venue_photo_proxy?id=<venue_id>&name=<restaurant_name>
    Proxy Google Places photo to bypass CORS restrictions
    """
    try:
        venue_id = req.args.get('id')
        restaurant_name = req.args.get('name')

        logger.info(f"[PHOTO-PROXY] Request for venue_id={venue_id}, name={restaurant_name}")

        if not venue_id:
            return {
                'success': False,
                'error': 'Missing venue_id parameter'
            }, 400

        if not restaurant_name:
            logger.warning(f"[PHOTO-PROXY] Missing restaurant name for venue_id={venue_id}")
            return {
                'success': False,
                'error': 'Missing restaurant name'
            }, 400

        # Fetch photo URL with caching
        photo_url = fetch_venue_photo_with_cache(venue_id, restaurant_name)
        logger.info(f"[PHOTO-PROXY] Fetched photo_url={photo_url} for {restaurant_name}")

        if not photo_url:
            logger.warning(f"[PHOTO-PROXY] No photo available for {restaurant_name} (venue_id={venue_id})")
            return {
                'success': False,
                'error': 'No photo available for this restaurant'
            }, 404

        # Fetch the image from Google Maps
        logger.info(f"[PHOTO-PROXY] Fetching image from Google Maps for {restaurant_name}")
        image_response = requests.get(photo_url, timeout=10)

        print("PHOTO URL:", photo_url)

        if image_response.status_code != 200:
            logger.error(f"[PHOTO-PROXY] Failed to fetch image. Status: {image_response.status_code}")
            return {
                'success': False,
                'error': 'Failed to fetch image from Google Maps',
                'message': image_response.text
            }, 500

        # Get content type from response or default to jpeg
        content_type = image_response.headers.get('Content-Type', 'image/jpeg')
        logger.info(f"[PHOTO-PROXY] Successfully fetched image for {restaurant_name}. Content-Type: {content_type}, Size: {len(image_response.content)} bytes")

        # For Cloud Functions, we need to return the image as a response
        # Firebase Functions Python SDK handles binary responses
        from firebase_functions.https_fn import Response

        return Response(
            response=image_response.content,
            status=200,
            headers={
                'Content-Type': content_type,
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=86400'  # Cache for 24 hours
            }
        )

    except requests.Timeout:
        logger.error(f"[PHOTO-PROXY] Timeout fetching image for venue_id={req.args.get('id')}")
        return {
            'success': False,
            'error': 'Timeout fetching image'
        }, 504
    except Exception as e:
        logger.error(f"[PHOTO-PROXY] Error proxying venue photo for venue_id={req.args.get('id')}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500
