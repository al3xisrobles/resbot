"""
Gemini AI Search Cloud Function for Resy Bot
Handles AI-powered restaurant reservation information using Google Gemini with Google Search grounding
"""

import logging
import requests
from datetime import date, timedelta

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from google.genai import types
from .utils import load_credentials, get_resy_headers, gemini_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def gemini_search(req: Request):
    """
    POST /gemini_search
    Get AI-powered summary about restaurant reservation details using Google Gemini with Google Search grounding
    Body should include:
    - restaurantName: Name of the restaurant (required)
    - venueId: Resy venue ID (optional, but recommended for better results)
    Query parameters:
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        data = req.get_json(silent=True) or {}
        restaurant_name = data.get('restaurantName')
        venue_id = data.get('venueId')
        user_id = req.args.get('userId')

        if not restaurant_name:
            return {
                'success': False,
                'error': 'Missing restaurant name'
            }, 400

        if not gemini_client:
            return {
                'success': False,
                'error': 'Gemini API not configured. Please set GEMINI_API_KEY environment variable.'
            }, 503

        # First, query Resy API to check available dates and determine booking window
        resy_findings = ""
        if venue_id:
            try:
                # Load credentials (from Firestore if userId provided, else from credentials.json)
                credentials = load_credentials(user_id)
                headers = get_resy_headers(credentials)

                # Use calendar API to get complete availability overview
                today = date.today()
                end_date = today + timedelta(days=90)  # Check up to 90 days out

                logger.info(f"Checking booking window for venue {venue_id} using calendar API")

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

                        logger.info(f"Final booking window from calendar: {max_booking_window} days (furthest scheduled date)")
                    else:
                        logger.warning(f"Calendar API returned status {resp.status_code}")
                        max_booking_window = 0

                except Exception as e:
                    logger.warning(f"Calendar API request failed: {str(e)}")
                    max_booking_window = 0

                # Generate findings
                if max_booking_window > 0:
                    resy_findings = f"\n\nIMPORTANT CONTEXT from Resy API: Based on checking the Resy calendar API directly, {restaurant_name} currently has reservations available up to {max_booking_window} days in advance. This suggests the booking window is approximately {max_booking_window} days."
                else:
                    resy_findings = f"\n\nNote: Checked Resy calendar API but no available reservation dates found in the next 90 days (restaurant may be fully booked or closed)."

            except Exception as e:
                logger.warning(f"Failed to query Resy API for booking window: {str(e)}")
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
            return {
                'success': False,
                'error': 'No response from Gemini API'
            }, 500

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

        return {
            'success': True,
            'data': response_data
        }

    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500
