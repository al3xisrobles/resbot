"""
Venue-related Cloud Functions for Resy Bot
Handles venue details and links
"""

import logging
from datetime import datetime, timedelta

import requests
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions, MemoryOption
from google.cloud import firestore as gc_firestore

from .response_schemas import (
    VenueBasicData,
    VenueDetailData,
    VenueLinksData,
    VenueLinksModel,
    VenuePaymentRequirementData,
    error_response,
    success_response,
)
from .resy_client.api_access import build_resy_client
from .resy_client.errors import ResyApiError
from .resy_client.models import CalendarRequestParams, FindRequestBody
from .sentry_utils import with_sentry_trace
from .utils import GOOGLE_MAPS_API_KEY, _get_firestore_client, load_credentials

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

        # Load credentials and fetch venue via resy_client
        config = load_credentials(user_id)
        client = build_resy_client(config)
        venue_data = client.get_venue(venue_id)

        venue_name = venue_data.name
        photo_urls = venue_data.images or []
        metadata = venue_data.metadata or {}
        description = metadata.get('description', '') if isinstance(metadata, dict) else ''
        location = venue_data.location
        address_1 = location.address_1 if location else ''
        locality = location.locality if location else ''
        region = location.region if location else ''
        neighborhood = location.neighborhood if location else ''
        address = f"{address_1}, {locality}, {region}" if location else 'N/A'
        rating = None
        if venue_data.rater and isinstance(venue_data.rater, list) and venue_data.rater:
            rating = venue_data.rater[0].get('score') if isinstance(venue_data.rater[0], dict) else None
        elif venue_data.rater and isinstance(venue_data.rater, dict):
            rating = venue_data.rater.get('score')

        venue_detail = VenueDetailData(
            name=venue_name,
            venue_id=venue_id,
            type=venue_data.type or 'N/A',
            address=address,
            neighborhood=neighborhood if isinstance(neighborhood, str) else '',
            price_range=venue_data.price_range_id or 0,
            rating=rating,
            photoUrls=photo_urls,
            description=description,
        )
        return success_response(venue_detail)

    except ResyApiError as e:
        logger.error(
            "Resy API error fetching venue: %s %s",
            e.status_code,
            e.response_body[:200] if e.response_body else "",
        )
        return {
            'success': False,
            'error': str(e)
        }, 500
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

        # First get venue details via resy_client
        logger.info("[VENUE-LINKS] Fetching venue details from Resy API...")
        credentials = load_credentials(user_id)
        client = build_resy_client(credentials)
        try:
            venue_data = client.get_venue(venue_id)
        except ResyApiError as e:
            logger.error(
                "[VENUE-LINKS] Failed to fetch venue details. Status: %s %s",
                e.status_code,
                e.response_body[:200] if e.response_body else "",
            )
            return {
                'success': False,
                'error': 'Failed to fetch venue details'
            }, 500

        restaurant_name = venue_data.name or ''
        location = venue_data.location
        city = location.locality if location else ''

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

                address_1 = location.address_1 if location else ""
                postal_code = getattr(location, "postal_code", "") or ""
                state = location.region if location else ""
                city = location.locality if location else ""

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
        logger.info("[VENUE-LINKS] Venue type: %s", venue_data.type)
        logger.info("[VENUE-LINKS] Location address_1: %s", location.address_1 if location else None)
        logger.info("[VENUE-LINKS] Location neighborhood: %s", getattr(location, "neighborhood", "") if location else "")
        logger.info("[VENUE-LINKS] Price range ID: %s", venue_data.price_range_id)
        logger.info("[VENUE-LINKS] Rating: %s", getattr(venue_data, "rating", None))

        venue_links_data = VenueLinksData(
            links=VenueLinksModel(googleMaps=links.get('googleMaps'), resy=links.get('resy')),
            venueData=VenueBasicData(
                name=restaurant_name,
                type=venue_data.type or '',
                address=location.address_1 if location else '',
                neighborhood=getattr(location, 'neighborhood', '') if location else '',
                priceRange=venue_data.price_range_id or 0,
                rating=getattr(venue_data, 'rating', 0) or 0
            )
        )
        return success_response(venue_links_data)

    except Exception as e:
        logger.error("[VENUE-LINKS] ✗ Error getting venue links: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(
    cors=CorsOptions(cors_origins="*", cors_methods=["GET"]),
    timeout_sec=60,
    memory=MemoryOption.GB_1,
)
@with_sentry_trace
def check_venue_payment_requirement(req: Request):
    """
    GET /check_venue_payment_requirement?id=<venue_id>&userId=<user_id>&date=<date>&partySize=<party_size>
    Check if venue requires payment method by analyzing /find endpoint slot payment data.
    Returns: {"success": true, "requiresPaymentMethod": true|false|null}
    - true: payment method required (any slot has is_paid=true OR deposit_fee != null OR cancellation_fee != null)
    - false: no payment method required (ALL slots have is_paid=false AND deposit_fee=null AND cancellation_fee=null)
    - null: unknown (no slots available to analyze)
    """
    try:
        venue_id = req.args.get('id')
        user_id = req.args.get('userId')
        date_str = req.args.get('date')
        party_size = int(req.args.get('partySize', 2))

        if not venue_id:
            resp, code = error_response('Missing venue_id', 400)
            return resp, code

        db = _get_firestore_client()
        venue_doc = db.collection('venues').document(venue_id).get()

        if venue_doc.exists:
            venue_data = venue_doc.to_dict()
            requires_payment = venue_data.get('requiresPaymentMethod')
            if requires_payment is not None:
                logger.info(
                    "Using cached payment requirement for venue %s: %s",
                    venue_id,
                    requires_payment,
                )
                return success_response(
                    VenuePaymentRequirementData(
                        requiresPaymentMethod=requires_payment,
                        source='cache',
                    )
                )

        config = load_credentials(user_id)
        client = build_resy_client(config)

        # If no date provided, find the first available date from calendar
        if not date_str:
            today = datetime.now()
            end_date = today + timedelta(days=90)
            
            calendar_params = CalendarRequestParams(
                venue_id=venue_id,
                num_seats=party_size,
                start_date=today.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
            )
            
            calendar_data = client.get_calendar(calendar_params)
            
            # Find dates that might have availability (not 'sold-out' or 'closed')
            candidate_dates = []
            if calendar_data.scheduled:
                for entry in calendar_data.scheduled:
                    if entry.inventory:
                        status = entry.inventory.reservation
                        # Try dates that are 'available' or any status that's not explicitly unavailable
                        if status in ['available', None] or status not in ['sold-out', 'closed']:
                            candidate_dates.append(entry.date)
                        if len(candidate_dates) >= 5:  # Try up to 5 dates
                            break
            
            # If no candidates from calendar, try next 5 days
            if not candidate_dates:
                for i in range(1, 6):
                    candidate_dates.append((today + timedelta(days=i)).strftime('%Y-%m-%d'))

            # Try each candidate date until we get a venue with slots or templates
            venue_result = None
            date_used = None
            for candidate_date in candidate_dates:
                find_request = FindRequestBody(
                    venue_id=int(venue_id),
                    day=candidate_date,
                    party_size=party_size,
                )
                venue_result = client.find_venue_result(find_request)
                if venue_result and (venue_result.slots or venue_result.templates):
                    date_used = candidate_date
                    break

            if not venue_result or (not venue_result.slots and not venue_result.templates):
                logger.info(
                    "No slots or templates found on any candidate date for venue %s",
                    venue_id,
                )
                return success_response(
                    VenuePaymentRequirementData(
                        requiresPaymentMethod=None,
                        source='no_slots_found',
                    )
                )
        else:
            # Date was provided, use it directly
            find_request = FindRequestBody(
                venue_id=int(venue_id),
                day=date_str,
                party_size=party_size,
            )
            venue_result = client.find_venue_result(find_request)
            date_used = date_str

        if not venue_result:
            logger.info("No venue result for venue %s on %s", venue_id, date_used)
            return success_response(
                VenuePaymentRequirementData(
                    requiresPaymentMethod=None,
                    source='find_no_slots',
                )
            )

        requires_payment = False
        source = 'find_slots'
        slots_analyzed = 0

        if venue_result.slots:
            for slot in venue_result.slots:
                payment = getattr(slot, 'payment', None)
                if payment:
                    if (
                        getattr(payment, 'is_paid', False)
                        or getattr(payment, 'deposit_fee', None) is not None
                        or getattr(payment, 'cancellation_fee', None) is not None
                    ):
                        requires_payment = True
                        break
            slots_analyzed = len(venue_result.slots)
        elif venue_result.templates:
            for _tid, t in venue_result.templates.items():
                if not isinstance(t, dict):
                    continue
                if t.get('is_paid') or t.get('deposit_fee') is not None or t.get('cancellation_fee') is not None:
                    requires_payment = True
                    break
            source = 'find_templates'

        db.collection('venues').document(venue_id).set(
            {
                'requiresPaymentMethod': requires_payment,
                'lastChecked': gc_firestore.SERVER_TIMESTAMP,
                'venueId': venue_id,
            },
            merge=True,
        )
        logger.info(
            "Cached payment requirement for venue %s: %s (source=%s)",
            venue_id,
            requires_payment,
            source,
        )

        data = VenuePaymentRequirementData(
            requiresPaymentMethod=requires_payment,
            source=source,
            slotsAnalyzed=slots_analyzed if slots_analyzed else None,
        )
        return success_response(data)

    except Exception as e:
        logger.error("Error checking venue payment requirement: %s", e)
        resp, code = error_response(str(e), 500)
        return resp, code
