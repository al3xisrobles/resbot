"""
Featured restaurants Cloud Functions for Resy Bot
Handles trending/climbing and top-rated restaurant lists
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption

from .cities import get_city_config
from .resy_client.api_access import build_resy_client
from .resy_client.errors import ResyApiError
from .sentry_utils import with_sentry_trace
from .utils import load_credentials

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _extract_resy_image_url(image_data):
    """
    Extract image URL from Resy API responsive_images data.

    Args:
        image_data: responsive_images dict from Resy API

    Returns:
        str: Image URL if found, None otherwise
    """
    if not image_data:
        return None

    urls = image_data.get('urls', {})
    if not urls:
        return None

    first_file = image_data.get('file_names', [None])[0]
    if not first_file or first_file not in urls:
        return None

    aspect_ratios = urls[first_file]

    # Try 1:1 aspect ratio at 400px first
    if '1:1' in aspect_ratios and '400' in aspect_ratios['1:1']:
        return aspect_ratios['1:1']['400']

    # Fallback: try any available size
    for sizes in aspect_ratios.values():
        for url in sizes.values():
            if url:
                return url

    return None


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]), timeout_sec=60, memory=MemoryOption.GB_1)
@with_sentry_trace
def climbing(req: Request):
    """
    GET /climbing?limit=<limit>&userId=<user_id>&city=<city_id>
    Get trending/climbing restaurants from Resy
    Query parameters:
    - limit: Number of restaurants to return (default: 10)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    - city: City ID (optional) - defaults to 'nyc'
    """
    try:
        limit = req.args.get('limit', '10')
        user_id = req.args.get('userId')
        city_id = req.args.get('city', 'nyc')

        # Load credentials and build Resy client
        config = load_credentials(user_id)
        client = build_resy_client(config)

        # Get city configuration and URL slug
        city_config = get_city_config(city_id)
        url_slug = city_config.get('url_slug', 'new-york-ny')

        logger.info("Fetching climbing restaurants for city slug: %s", url_slug)
        try:
            data = client.get_city_list(url_slug, 'climbing', int(limit))
        except ResyApiError as e:
            logger.error("Resy API error fetching climbing list: %s %s", e.status_code, e.endpoint)
            return {
                'success': False,
                'error': str(e)
            }, 500

        venues = data.results.venues if data.results else []
        logger.info("Resy API returned %s venues", len(venues))

        # The list endpoint doesn't return geo coordinates, so we need to fetch them
        # from the /3/venue endpoint for each venue via client
        def fetch_venue_coords(venue_id):
            """Fetch coordinates for a single venue"""
            try:
                venue_data = client.get_venue(venue_id)
                location = venue_data.location
                lat = location.latitude if location else None
                lng = location.longitude if location else None
                return {'lat': lat, 'lng': lng}
            except ResyApiError:
                return {'lat': None, 'lng': None}
            except Exception as e:
                logger.warning("Failed to fetch coordinates for venue %s: %s", venue_id, e)
                return {'lat': None, 'lng': None}

        # Fetch coordinates in parallel
        venue_coords = {}
        venue_ids = [str(v.get('id', {}).get('resy', '')) for v in venues if v.get('id', {}).get('resy')]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_venue = {
                executor.submit(fetch_venue_coords, venue_id): venue_id 
                for venue_id in venue_ids
            }
            for future in as_completed(future_to_venue):
                venue_id = future_to_venue[future]
                try:
                    coords = future.result()
                    venue_coords[venue_id] = coords
                except Exception as e:
                    logger.warning("Error fetching coordinates for venue %s: %s", venue_id, e)
                    venue_coords[venue_id] = {'lat': None, 'lng': None}

        # Transform the data to match our frontend structure
        restaurants = []
        venues_without_geo = 0
        for venue in venues:
            venue_id = str(venue.get('id', {}).get('resy', ''))
            location = venue.get('location', {})
            image_data = venue.get('responsive_images', {})

            # Extract image URL directly from Resy data
            image_url = _extract_resy_image_url(image_data)

            # Get coordinates from our fetched data
            coords = venue_coords.get(venue_id, {'lat': None, 'lng': None})
            lat = coords.get('lat')
            lng = coords.get('lng')
            
            if lat is None or lng is None:
                venues_without_geo += 1

            restaurants.append({
                'id': venue_id,
                'name': venue.get('name', ''),
                'type': venue.get('type', ''),
                'priceRange': venue.get('price_range_id', 0),
                'location': {
                    'neighborhood': location.get('neighborhood', ''),
                    'locality': location.get('locality', ''),
                    'region': location.get('region', ''),
                    'address': location.get('address_1', '')
                },
                'imageUrl': image_url,
                'rating': venue.get('rater', [{}])[0].get('score') if venue.get('rater') else None,
                'lat': lat,
                'lng': lng
            })

        logger.info("Fetched %s climbing restaurants (%s without geo coordinates)", 
                  len(restaurants), venues_without_geo)

        return {
            'success': True,
            'data': restaurants
        }

    except Exception as e:
        logger.error("Error fetching climbing restaurants: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]), timeout_sec=60, memory=MemoryOption.GB_1)
@with_sentry_trace
def top_rated(req: Request):
    """
    GET /top_rated?limit=<limit>&userId=<user_id>&city=<city_id>
    Get top-rated restaurants from Resy
    Query parameters:
    - limit: Number of restaurants to return (default: 10)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    - city: City ID (optional) - defaults to 'nyc'
    """
    try:
        limit = req.args.get('limit', '10')
        user_id = req.args.get('userId')
        city_id = req.args.get('city', 'nyc')

        # Load credentials and build Resy client
        config = load_credentials(user_id)
        client = build_resy_client(config)

        # Get city configuration and URL slug
        city_config = get_city_config(city_id)
        url_slug = city_config.get('url_slug', 'new-york-ny')

        logger.info("Fetching top-rated restaurants for city slug: %s", url_slug)
        try:
            data = client.get_city_list(url_slug, 'top-rated', int(limit))
        except ResyApiError as e:
            logger.error("Resy API error fetching top-rated list: %s %s", e.status_code, e.endpoint)
            return {
                'success': False,
                'error': str(e)
            }, 500

        venues = data.results.venues if data.results else []
        logger.info("Resy API returned %s venues", len(venues))

        # The list endpoint doesn't return geo coordinates, so we need to fetch them
        # from the /3/venue endpoint for each venue via client
        def fetch_venue_coords(venue_id):
            """Fetch coordinates for a single venue"""
            try:
                venue_data = client.get_venue(venue_id)
                location = venue_data.location
                lat = location.latitude if location else None
                lng = location.longitude if location else None
                return {'lat': lat, 'lng': lng}
            except ResyApiError:
                return {'lat': None, 'lng': None}
            except Exception as e:
                logger.warning("Failed to fetch coordinates for venue %s: %s", venue_id, e)
                return {'lat': None, 'lng': None}

        # Fetch coordinates in parallel
        venue_coords = {}
        venue_ids = [str(v.get('id', {}).get('resy', '')) for v in venues if v.get('id', {}).get('resy')]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_venue = {
                executor.submit(fetch_venue_coords, venue_id): venue_id 
                for venue_id in venue_ids
            }
            for future in as_completed(future_to_venue):
                venue_id = future_to_venue[future]
                try:
                    coords = future.result()
                    venue_coords[venue_id] = coords
                except Exception as e:
                    logger.warning("Error fetching coordinates for venue %s: %s", venue_id, e)
                    venue_coords[venue_id] = {'lat': None, 'lng': None}

        # Transform the data to match our frontend structure
        restaurants = []
        venues_without_geo = 0
        for venue in venues:
            venue_id = str(venue.get('id', {}).get('resy', ''))
            location = venue.get('location', {})
            image_data = venue.get('responsive_images', {})

            # Extract image URL directly from Resy data
            image_url = _extract_resy_image_url(image_data)

            # Get coordinates from our fetched data
            coords = venue_coords.get(venue_id, {'lat': None, 'lng': None})
            lat = coords.get('lat')
            lng = coords.get('lng')
            
            if lat is None or lng is None:
                venues_without_geo += 1

            restaurants.append({
                'id': venue_id,
                'name': venue.get('name', ''),
                'type': venue.get('type', ''),
                'priceRange': venue.get('price_range_id', 0),
                'location': {
                    'neighborhood': location.get('neighborhood', ''),
                    'locality': location.get('locality', ''),
                    'region': location.get('region', ''),
                    'address': location.get('address_1', '')
                },
                'imageUrl': image_url,
                'rating': venue.get('rater', [{}])[0].get('score') if venue.get('rater') else None,
                'lat': lat,
                'lng': lng
            })

        logger.info("Fetched %s top-rated restaurants (%s without geo coordinates)", 
                  len(restaurants), venues_without_geo)

        return {
            'success': True,
            'data': restaurants
        }

    except Exception as e:
        logger.error("Error fetching top-rated restaurants: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500
