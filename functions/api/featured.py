"""
Featured restaurants Cloud Functions for Resy Bot
Handles trending/climbing and top-rated restaurant lists
"""

import logging
import requests

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from .utils import load_credentials, get_resy_headers

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


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def climbing(req: Request):
    """
    GET /climbing?limit=<limit>&userId=<user_id>
    Get trending/climbing restaurants from Resy
    Query parameters:
    - limit: Number of restaurants to return (default: 10)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        limit = req.args.get('limit', '10')
        user_id = req.args.get('userId')

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Query the climbing endpoint
        url = f'https://api.resy.com/3/cities/new-york-ny/list/climbing?limit={limit}'
        logger.info("Fetching climbing restaurants from: %s", url)

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        data = response.json()
        venues = data.get('results', {}).get('venues', [])

        # Transform the data to match our frontend structure
        restaurants = []
        for venue in venues:
            location = venue.get('location', {})
            image_data = venue.get('responsive_images', {})

            # Extract image URL directly from Resy data
            image_url = _extract_resy_image_url(image_data)

            restaurants.append({
                'id': str(venue.get('id', {}).get('resy', '')),
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
                'rating': venue.get('rater', [{}])[0].get('score') if venue.get('rater') else None
            })

        logger.info("Fetched %s climbing restaurants", len(restaurants))

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


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def top_rated(req: Request):
    """
    GET /top_rated?limit=<limit>&userId=<user_id>
    Get top-rated restaurants from Resy
    Query parameters:
    - limit: Number of restaurants to return (default: 10)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        limit = req.args.get('limit', '10')
        user_id = req.args.get('userId')

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Query the top-rated endpoint
        url = f'https://api.resy.com/3/cities/new-york-ny/list/top-rated?limit={limit}'
        logger.info("Fetching top-rated restaurants from: %s", url)

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

        data = response.json()
        venues = data.get('results', {}).get('venues', [])

        # Transform the data to match our frontend structure
        restaurants = []
        for venue in venues:
            location = venue.get('location', {})
            image_data = venue.get('responsive_images', {})

            # Extract image URL directly from Resy data
            image_url = _extract_resy_image_url(image_data)

            restaurants.append({
                'id': str(venue.get('id', {}).get('resy', '')),
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
                'rating': venue.get('rater', [{}])[0].get('score') if venue.get('rater') else None
            })

        logger.info("Fetched %s top-rated restaurants", len(restaurants))

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
