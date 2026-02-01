"""
Featured restaurants Cloud Functions for Resy Bot
Handles trending/climbing and top-rated restaurant lists
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption

from .sentry_utils import with_sentry_trace
from .utils import load_credentials, get_resy_headers
from .cities import get_city_config

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

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Get city configuration and URL slug
        city_config = get_city_config(city_id)
        url_slug = city_config.get('url_slug', 'new-york-ny')

        # Query the climbing endpoint
        url = f'https://api.resy.com/3/cities/{url_slug}/list/climbing?limit={limit}'
        logger.info("Fetching climbing restaurants from: %s", url)

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        data = response.json()
        venues = data.get('results', {}).get('venues', [])
        logger.info("Resy API returned %s venues", len(venues))

        # The list endpoint doesn't return geo coordinates, so we need to fetch them
        # from the /3/venue endpoint for each venue
        def fetch_venue_coords(venue_id):
            """Fetch coordinates for a single venue"""
            try:
                venue_response = requests.get(
                    'https://api.resy.com/3/venue',
                    params={'id': venue_id},
                    headers=headers,
                    timeout=10
                )
                if venue_response.status_code == 200:
                    venue_data = venue_response.json()
                    location = venue_data.get('location', {})
                    
                    # Coordinates are directly in location object as 'latitude' and 'longitude'
                    lat = location.get('latitude')
                    lng = location.get('longitude')
                    
                    return {
                        'lat': lat,
                        'lng': lng
                    }
                else:
                    logger.warning("Venue %s: API returned status %s", venue_id, venue_response.status_code)
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

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Get city configuration and URL slug
        city_config = get_city_config(city_id)
        url_slug = city_config.get('url_slug', 'new-york-ny')

        # Query the top-rated endpoint
        url = f'https://api.resy.com/3/cities/{url_slug}/list/top-rated?limit={limit}'
        logger.info("Fetching top-rated restaurants from: %s", url)

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        data = response.json()
        venues = data.get('results', {}).get('venues', [])
        logger.info("Resy API returned %s venues", len(venues))

        # The list endpoint doesn't return geo coordinates, so we need to fetch them
        # from the /3/venue endpoint for each venue
        def fetch_venue_coords(venue_id):
            """Fetch coordinates for a single venue"""
            try:
                venue_response = requests.get(
                    'https://api.resy.com/3/venue',
                    params={'id': venue_id},
                    headers=headers,
                    timeout=10
                )
                if venue_response.status_code == 200:
                    venue_data = venue_response.json()
                    location = venue_data.get('location', {})
                    
                    # Coordinates are directly in location object as 'latitude' and 'longitude'
                    lat = location.get('latitude')
                    lng = location.get('longitude')
                    
                    return {
                        'lat': lat,
                        'lng': lng
                    }
                else:
                    logger.warning("Venue %s: API returned status %s", venue_id, venue_response.status_code)
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
