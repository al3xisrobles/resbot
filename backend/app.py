"""
Flask server for Resy Bot
Handles all API endpoints including restaurant search, venue details, reservations, and AI summaries
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

# Add resy_bot to path
import sys
sys.path.insert(0, os.path.dirname(__file__))

from api.models import ResyConfig, TimedReservationRequest
from api.manager import ResyManager

app = Flask(__name__)
CORS(app)

# Configuration
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', '')

# Initialize Gemini AI client if API key is available
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def load_credentials():
    """Load Resy credentials from credentials.json"""
    with open(CREDENTIALS_PATH, 'r') as f:
        return json.load(f)


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


@app.route('/api/search', methods=['GET'])
def search_venues():
    """
    GET /api/search
    Search for restaurants by name (NYC only)
    """
    try:
        query = request.args.get('query')

        if not query:
            return jsonify({
                'success': False,
                'error': 'Missing search query'
            }), 400

        # Load credentials
        config = load_credentials()
        headers = get_resy_headers(config)

        # Search payload
        payload = {
            "geo": {
                "latitude": 40.7157,
                "longitude": -74
            },
            "highlight": {
                "pre_tag": "<b>",
                "post_tag": "</b>"
            },
            "per_page": 20,
            "query": query,
            "slot_filter": {
                "day": "2025-12-11",
                "party_size": 2
            },
            "types": ["venue", "cuisine"]
        }

        response = requests.post(
            'https://api.resy.com/3/venuesearch/search',
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'API returned status {response.status_code}: {response.text[:200]}'
            }), 500

        data = response.json()

        # Extract venues from search results
        hits = data.get('search', {}).get('hits', [])
        results = []

        for hit in hits:
            venue = hit.get('_source') or hit

            if not venue or not venue.get('name'):
                continue

            # Filter to NYC only
            locality = venue.get('locality', '')
            region = venue.get('region', '')
            if locality != 'New York' or region != 'NY':
                continue

            location = venue.get('location', {})
            venue_id = venue.get('id', {}).get('resy') if isinstance(venue.get('id'), dict) else venue.get('id')

            results.append({
                'id': venue_id or 'unknown',
                'name': venue.get('name', 'Unknown'),
                'locality': venue.get('locality', 'N/A'),
                'region': venue.get('region', 'N/A'),
                'neighborhood': venue.get('neighborhood', 'N/A'),
                'type': venue.get('type', 'N/A'),
                'price_range': venue.get('price_range_id') or venue.get('price_range', 0),
                'address': f"{location.get('address_1', '')}, {venue.get('locality', '')}, {venue.get('region', '')}" if location.get('address_1') else None
            })

        return jsonify({
            'success': True,
            'data': results
        })

    except Exception as e:
        app.logger.error(f"Error searching venues: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/venue/<venue_id>', methods=['GET'])
def get_venue(venue_id):
    """
    GET /api/venue/:venueId
    Get restaurant information by venue ID
    """
    try:
        # Load credentials
        config = load_credentials()
        headers = get_resy_headers(config)

        response = requests.get(
            'https://api.resy.com/3/venue',
            params={'id': venue_id},
            headers=headers
        )

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'API returned status {response.status_code}'
            }), 500

        venue_data = response.json()

        return jsonify({
            'success': True,
            'data': {
                'name': venue_data.get('name'),
                'venue_id': venue_id,
                'type': venue_data.get('type', 'N/A'),
                'address': f"{venue_data.get('location', {}).get('address_1', '')}, {venue_data.get('location', {}).get('locality', '')}, {venue_data.get('location', {}).get('region', '')}" if venue_data.get('location') else 'N/A',
                'neighborhood': venue_data.get('location', {}).get('neighborhood', 'N/A'),
                'price_range': venue_data.get('price_range_id', 0),
                'rating': venue_data.get('rating')
            }
        })

    except Exception as e:
        app.logger.error(f"Error fetching venue: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reservation', methods=['POST'])
def make_reservation():
    """
    POST /api/reservation
    Create a reservation request
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['venueId', 'partySize', 'date', 'hour', 'minute']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        # Load credentials
        credentials = load_credentials()
        config = ResyConfig(**credentials)

        # Build reservation request
        reservation_data = {
            'reservation_request': {
                'party_size': int(data['partySize']),
                'venue_id': data['venueId'],
                'window_hours': int(data.get('windowHours', 1)),
                'prefer_early': False,
                'ideal_date': data['date'],
                'ideal_hour': int(data['hour']),
                'ideal_minute': int(data['minute']),
                'preferred_type': data.get('seatingType') if data.get('seatingType') != 'any' else None
            },
            'expected_drop_hour': int(data.get('dropHour', 9)),
            'expected_drop_minute': int(data.get('dropMinute', 0))
        }

        timed_request = TimedReservationRequest(**reservation_data)

        # Make reservation
        manager = ResyManager.build(config)
        resy_token = manager.make_reservation_at_opening_time(timed_request)

        return jsonify({
            'success': True,
            'message': 'Reservation request submitted successfully',
            'resy_token': resy_token
        })

    except Exception as e:
        app.logger.error(f"Error making reservation: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gemini-search', methods=['POST'])
def gemini_search():
    """
    POST /api/gemini-search
    Get AI-powered summary about restaurant reservation details using Google Gemini with Google Search grounding
    """
    try:
        data = request.json
        restaurant_name = data.get('restaurantName')
        venue_id = data.get('venueId')

        if not restaurant_name:
            return jsonify({
                'success': False,
                'error': 'Missing restaurant name'
            }), 400

        if not gemini_client:
            return jsonify({
                'success': False,
                'error': 'Gemini API not configured. Please set GEMINI_API_KEY environment variable.'
            }), 503

        # First, query Resy API to check available dates and determine booking window
        resy_findings = ""
        if venue_id:
            try:
                from datetime import date, timedelta

                # Load credentials
                credentials = load_credentials()
                headers = get_resy_headers(credentials)

                # Use calendar API to get complete availability overview
                today = date.today()
                end_date = today + timedelta(days=90)  # Check up to 90 days out

                app.logger.info(f"Checking booking window for venue {venue_id} using calendar API")

                # Query calendar API
                params = {
                    'venue_id': venue_id,
                    'num_seats': 2,
                    'start_date': today.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }

                try:
                    resp = requests.get(
                        'https://api.resy.com/4/venue/calendar',
                        params=params,
                        headers=headers,
                        timeout=5
                    )

                    max_booking_window = 0

                    if resp.ok:
                        calendar_data = resp.json()
                        scheduled = calendar_data.get('scheduled', [])

                        # Find the furthest date in the scheduled array
                        # Each date in 'scheduled' is a date the restaurant has made available for reservations
                        # (regardless of whether slots are sold out or not)
                        for entry in scheduled:
                            entry_date = entry.get('date')
                            if entry_date:
                                # Calculate days from today
                                entry_date_obj = date.fromisoformat(entry_date)
                                days_ahead = (entry_date_obj - today).days

                                if days_ahead > max_booking_window:
                                    max_booking_window = days_ahead

                        app.logger.info(f"Final booking window from calendar: {max_booking_window} days (furthest scheduled date)")
                    else:
                        app.logger.warning(f"Calendar API returned status {resp.status_code}")
                        max_booking_window = 0

                except Exception as e:
                    app.logger.warning(f"Calendar API request failed: {str(e)}")
                    max_booking_window = 0

                # Generate findings
                if max_booking_window > 0:
                    resy_findings = f"\n\nIMPORTANT CONTEXT from Resy API: Based on checking the Resy calendar API directly, {restaurant_name} currently has reservations available up to {max_booking_window} days in advance. This suggests the booking window is approximately {max_booking_window} days."
                else:
                    resy_findings = f"\n\nNote: Checked Resy calendar API but no available reservation dates found in the next 90 days (restaurant may be fully booked or closed)."

            except Exception as e:
                app.logger.warning(f"Failed to query Resy API for booking window: {str(e)}")
                resy_findings = ""

        # Create search query
        search_query = f"When do {restaurant_name} reservations open in NYC? What time and how many days in advance?"

        # Configure Google Search grounding tool
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.3,
        )

        print(resy_findings)

        prompt = f"""You are a helpful assistant providing restaurant reservation information.

Question: {search_query}{resy_findings}

Provide a concise summary (3-5 sentences, max 500 tokens) including:
- What time reservations typically open (e.g., 9:00 AM, 10:00 AM, midnight)
- How many days in advance reservations are released (e.g., 14 days, 30 days, 2 weeks). If, no matter what day today is, the entire next month is released (e.g., if it's Nov 20th but all of Dec 1 - 31st is released), specify that—i.e., specifically state if it's "30 days out" or "the entire next month".
- Do NOT mention that you can book through Resy. You MAY say the word Resy, but no need to say "RESTAURANT reservations are released on Resy." specifically.
- Do NOT give generic booking advice like "To secure a table, it is recommended to book precisely when the reservation window opens."
- DO give restaurant-specific booking advice like "For those unable to secure a reservation, the bar at Torrisi accommodates walk-ins on a first-come, first-served basis, offering the full menu."

If Resy API context is provided above, use it to confirm or verify the booking window from web search results.
"""

        # Call Gemini with Google Search grounding
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=config,
        )

        # Extract grounding metadata
        candidate = response.candidates[0] if response.candidates else None
        if not candidate:
            return jsonify({
                'success': False,
                'error': 'No response from Gemini API'
            }), 500

        grounding_metadata = candidate.grounding_metadata

        # Parse web search queries
        web_search_queries = []
        if grounding_metadata and grounding_metadata.web_search_queries:
            web_search_queries = grounding_metadata.web_search_queries

        # Parse grounding chunks (limit to top 6)
        grounding_chunks = []
        if grounding_metadata and grounding_metadata.grounding_chunks:
            for i, chunk in enumerate(grounding_metadata.grounding_chunks[:6]):
                chunk_data = {
                    'index': i,
                    'title': chunk.web.title if chunk.web else 'N/A',
                    'uri': chunk.web.uri if chunk.web else None,
                    'snippet': getattr(chunk, 'snippet', None) or (chunk.web.uri if chunk.web else None)
                }
                grounding_chunks.append(chunk_data)

        # Parse grounding supports
        grounding_supports = []
        if grounding_metadata and grounding_metadata.grounding_supports:
            for support in grounding_metadata.grounding_supports:
                support_data = {
                    'segment': {
                        'startIndex': support.segment.start_index if support.segment else None,
                        'endIndex': support.segment.end_index if support.segment else None,
                        'text': support.segment.text if support.segment else None
                    },
                    'groundingChunkIndices': support.grounding_chunk_indices or [],
                    'confidenceScores': support.confidence_scores or []
                }
                grounding_supports.append(support_data)

        # Extract summary from response text
        summary = response.text

        # Generate key facts from grounding chunks
        key_facts = []
        for i, chunk in enumerate(grounding_chunks[:4]):
            if chunk['snippet']:
                key_facts.append({
                    'fact': chunk['snippet'][:200],
                    'citationIndices': [i]
                })

        # Generate suggested follow-ups
        suggested_follow_ups = [
            f"What are the best times to try booking at {restaurant_name}?",
            f"Are there alternatives to {restaurant_name} in NYC?",
            f"What should I know before dining at {restaurant_name}?"
        ]

        print("\nSUMMARY:\n", summary)

        # Build response matching the requested structure
        response_data = {
            'summary': summary,
            'keyFacts': key_facts,
            'webSearchQueries': web_search_queries,
            'groundingChunks': grounding_chunks,
            'groundingSupports': grounding_supports,
            'rawGroundingMetadata': {
                'retrievalQueries': web_search_queries,
                'searchEntryPoint': grounding_metadata.search_entry_point.rendered_content if grounding_metadata and grounding_metadata.search_entry_point else None
            },
            'suggestedFollowUps': suggested_follow_ups[:3]
        }

        return jsonify({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        app.logger.error(f"Error calling Gemini API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/calendar/<venue_id>', methods=['GET'])
def get_calendar(venue_id):
    """
    GET /api/calendar/:venueId
    Get restaurant availability calendar
    """
    try:
        from datetime import date, timedelta

        # Load credentials
        config = load_credentials()
        headers = get_resy_headers(config)

        # Get party size from query params (default to 2)
        party_size = request.args.get('partySize', '2')

        # Query calendar API for 90 days
        today = date.today()
        end_date = today + timedelta(days=90)

        params = {
            'venue_id': venue_id,
            'num_seats': int(party_size),
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

        response = requests.get(
            'https://api.resy.com/4/venue/calendar',
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'API returned status {response.status_code}'
            }), 500

        calendar_data = response.json()
        scheduled = calendar_data.get('scheduled', [])

        # Transform the data for frontend
        availability = []
        for entry in scheduled:
            date_str = entry.get('date')
            inventory = entry.get('inventory', {})
            reservation_status = inventory.get('reservation')

            availability.append({
                'date': date_str,
                'available': reservation_status == 'available',
                'soldOut': reservation_status == 'sold-out' or reservation_status == 'not available',
                'closed': reservation_status == 'closed'
            })

        return jsonify({
            'success': True,
            'data': {
                'availability': availability,
                'startDate': today.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        app.logger.error(f"Error fetching calendar: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/venue/<venue_id>/photo', methods=['GET'])
def get_venue_photo(venue_id):
    """
    GET /api/venue/:venueId/photo
    Get Google Places photo URL for a restaurant
    """
    try:
        restaurant_name = request.args.get('name')

        if not restaurant_name:
            return jsonify({
                'success': False,
                'error': 'Missing restaurant name'
            }), 400

        if not GOOGLE_PLACES_API_KEY:
            return jsonify({
                'success': False,
                'error': 'Google Places API key not configured'
            }), 503

        # Search for the restaurant using Google Places Text Search API
        search_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        search_params = {
            'query': f"{restaurant_name} restaurant New York",
            'key': GOOGLE_PLACES_API_KEY
        }

        app.logger.info(f"Searching Google Places for: {restaurant_name}")

        search_response = requests.get(search_url, params=search_params, timeout=10)

        if search_response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Google Places API returned status {search_response.status_code}'
            }), 500

        search_data = search_response.json()

        # Check if we got results
        if not search_data.get('results') or len(search_data['results']) == 0:
            return jsonify({
                'success': False,
                'error': 'No restaurant found'
            }), 404

        # Get the first result
        place = search_data['results'][0]

        # Check if place has photos
        if not place.get('photos') or len(place['photos']) == 0:
            return jsonify({
                'success': False,
                'error': 'No photos available for this restaurant'
            }), 404

        # Get the photo reference from the first photo
        photo_reference = place['photos'][0]['photo_reference']

        # Construct the Google Places Photo URL with high quality
        # The frontend will use this URL to load the image directly from Google
        # Using maxwidth=1600 for high quality images (Google's max is 1600)
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1600&photo_reference={photo_reference}&key={GOOGLE_PLACES_API_KEY}"

        app.logger.info(f"Found photo for {restaurant_name}")

        return jsonify({
            'success': True,
            'data': {
                'photoUrl': photo_url,
                'placeName': place.get('name'),
                'placeAddress': place.get('formatted_address')
            }
        })

    except Exception as e:
        app.logger.error(f"Error fetching venue photo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    GET /api/health
    Health check endpoint
    """
    return jsonify({
        'status': 'ok',
        'timestamp': None  # Will be set by Flask automatically
    })


if __name__ == '__main__':
    print("\n🚀 Resy Bot Flask Server starting...")
    print("📍 API endpoints:")
    print("   GET  /api/search                  - Search restaurants by name")
    print("   GET  /api/venue/<venueId>         - Get restaurant by ID")
    print("   GET  /api/venue/<venueId>/photo   - Get restaurant photo URL")
    print("   GET  /api/calendar/<venueId>      - Get restaurant availability calendar")
    print("   POST /api/reservation             - Make reservation")
    print("   POST /api/gemini-search           - Get AI reservation summary")
    print("   GET  /api/health                  - Health check\n")

    port = int(os.getenv('PORT', 3001))
    app.run(host='0.0.0.0', port=port, debug=True)
