"""
Featured restaurants Cloud Functions for Resy Bot
Handles trending/climbing and top-rated restaurant lists
"""

import logging
import requests

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from .utils import load_credentials, get_resy_headers, fetch_venue_photo

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        logger.info(f"Fetching climbing restaurants from: {url}")

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
            venue_id = str(venue.get('id', {}).get('resy', ''))
            venue_name = venue.get('name', '')

            # Fetch image with comprehensive logging
            image_url = fetch_venue_photo(venue_id, venue_name, image_data)

            restaurants.append({
                'id': venue_id,
                'name': venue_name,
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

        logger.info(f"Fetched {len(restaurants)} climbing restaurants")

        return {
            'success': True,
            'data': restaurants
        }

    except Exception as e:
        logger.error(f"Error fetching climbing restaurants: {str(e)}")
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
        logger.info(f"Fetching top-rated restaurants from: {url}")

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
            venue_id = str(venue.get('id', {}).get('resy', ''))
            venue_name = venue.get('name', '')

            # Fetch image with comprehensive logging
            image_url = fetch_venue_photo(venue_id, venue_name, image_data)

            restaurants.append({
                'id': venue_id,
                'name': venue_name,
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

        logger.info(f"Fetched {len(restaurants)} top-rated restaurants")

        return {
            'success': True,
            'data': restaurants
        }

    except Exception as e:
        logger.error(f"Error fetching top-rated restaurants: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500
