"""
Gemini AI Search Cloud Function for Resy Bot
Handles AI-powered restaurant reservation information using Google Gemini with Google Search grounding
"""

import logging
from datetime import date, timedelta

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption

from google.genai import types

from .cities import get_city_config
from .resy_client.api_access import build_resy_client
from .resy_client.models import CalendarRequestParams
from .sentry_utils import with_sentry_trace
from .utils import load_credentials, gemini_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]), timeout_sec=60, memory=MemoryOption.GB_1)
@with_sentry_trace
def gemini_search(req: Request):
    """
    POST /gemini_search
    Get AI-powered summary about restaurant reservation details using Google Gemini with Google Search grounding
    Body should include:
    - restaurantName: Name of the restaurant (required)
    - venueId: Resy venue ID (optional, but recommended for better results)
    - city: Optional city ID (default: 'nyc')
    Query parameters:
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        data = req.get_json(silent=True) or {}
        restaurant_name = data.get('restaurantName')
        venue_id = data.get('venueId')
        city_id = data.get('city', 'nyc')
        user_id = req.args.get('userId')

        # Get city configuration
        city_config = get_city_config(city_id)
        city_name = city_config['name']

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

        # Load Resy client once if venue_id is provided (for both calendar and venue API calls)
        client = None
        if venue_id:
            try:
                credentials = load_credentials(user_id)
                client = build_resy_client(credentials)
            except Exception as e:
                logger.warning("Failed to load credentials: %s", e)
                client = None

        # First, query Resy API to check available dates and determine booking window
        resy_findings = ""
        if venue_id and client:
            try:

                # Use calendar API to get complete availability overview
                today = date.today()
                end_date = today + timedelta(days=90)  # Check up to 90 days out

                logger.info("Checking booking window for venue %s using calendar API", venue_id)

                calendar_params = CalendarRequestParams(
                    venue_id=venue_id,
                    num_seats=2,
                    start_date=today.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                )

                try:
                    calendar_data = client.get_calendar(calendar_params)
                    scheduled = calendar_data.scheduled or []
                    max_booking_window = 0

                    for entry in scheduled:
                        entry_date = entry.date
                        if entry_date:
                            entry_date_obj = date.fromisoformat(entry_date)
                            days_ahead = (entry_date_obj - today).days
                            max_booking_window = max(max_booking_window, days_ahead)

                    logger.info(
                        "Final booking window from calendar: %s days (furthest scheduled date)",
                        max_booking_window,
                    )
                except Exception as e:
                    logger.warning("Calendar API request failed: %s", e)
                    max_booking_window = 0

                # Generate findings
                if max_booking_window > 0:
                    resy_findings = (
                        f"\n\nIMPORTANT CONTEXT from Resy API: Based on checking the Resy "
                        f"calendar API directly, {restaurant_name} currently has reservations "
                        f"available up to {max_booking_window} days in advance. This suggests "
                        f"the booking window is approximately {max_booking_window} days."
                    )
                else:
                    resy_findings = (
                        "\n\nNote: Checked Resy calendar API but no available reservation dates "
                        "found in the next 90 days (restaurant may be fully booked or closed)."
                    )

            except Exception as e:
                logger.warning("Failed to query Resy API for booking window: %s", e)
                resy_findings = ""

        # Fetch venue content from /3/venue API for authoritative reservation info
        resy_venue_info = ""
        if venue_id and client:
            try:
                logger.info("Fetching venue content for venue %s", venue_id)

                venue_data = client.get_venue(venue_id)
                content_array = venue_data.content if isinstance(venue_data.content, list) else []

                    # Extract relevant content sections
                    extracted_content = []
                    for content_item in content_array:
                        if not isinstance(content_item, dict):
                            continue
                        content_name = content_item.get('name', '')
                        content_body = content_item.get('body', '')

                        # Prioritize need_to_know (reservation policy), then about, then why_we_like_it
                        if content_name == 'need_to_know' and content_body:
                            extracted_content.append(
                                f"RESERVATION POLICY: {content_body}"
                            )
                        elif content_name == 'about' and content_body:
                            extracted_content.append(
                                f"ABOUT: {content_body}"
                            )
                        elif content_name == 'why_we_like_it' and content_body:
                            extracted_content.append(
                                f"WHY WE LIKE IT: {content_body}"
                            )

                    if extracted_content:
                        resy_venue_info = (
                            "\n\nOFFICIAL RESY VENUE INFO (from restaurant's Resy page):\n"
                            + "\n\n".join(extracted_content)
                        )
                        logger.info(
                            "Extracted %s content sections from venue API",
                            len(extracted_content)
                        )

            except Exception as e:
                logger.warning("Failed to fetch venue content: %s", e)
                resy_venue_info = ""

        # Create search query
        search_query = f"When do {restaurant_name} reservations open in {city_name}? What time and how many days in advance?"

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

Question: {search_query}{resy_findings}{resy_venue_info}

Provide a concise summary (3-5 sentences, max 500 tokens) including:
- What time reservations typically open (e.g., 9:00 AM, 10:00 AM, midnight)
- How many days in advance reservations are released (e.g., 14 days, 30 days, 2 weeks). If, no matter what day today is, the entire next month is released (e.g., if it's Nov 20th but all of Dec 1 - 31st is released), specify that—i.e., specifically state if it's "30 days out" or "the entire next month".
- Do NOT mention that you can book through Resy. You MAY say the word Resy, but no need to say "RESTAURANT reservations are released on Resy." specifically.
- Do NOT give generic booking advice like "To secure a table, it is recommended to book precisely when the reservation window opens."
- DO give restaurant-specific booking advice like "For those unable to secure a reservation, the bar at Torrisi accommodates walk-ins on a first-come, first-served basis, offering the full menu."

IMPORTANT: If "OFFICIAL RESY VENUE INFO" is provided above, prioritize that information over web search results. The official venue info comes directly from the restaurant's Resy page and is the most authoritative source for reservation policies, booking windows, and restaurant-specific details.
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
            f"Are there alternatives to {restaurant_name} in {city_name}?",
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
                'searchEntryPoint': (
                    grounding_metadata.search_entry_point.rendered_content
                    if grounding_metadata and grounding_metadata.search_entry_point
                    else None
                )
            },
            'suggestedFollowUps': suggested_follow_ups[:3]
        }

        return {
            'success': True,
            'data': response_data
        }

    except Exception as e:
        logger.error("Error calling Gemini API: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500
