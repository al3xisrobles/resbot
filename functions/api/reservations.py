"""
Reservation-related Cloud Functions for Resy Bot
Handles calendar availability and reservation creation
"""

import logging
import traceback
from datetime import date, timedelta

import requests
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from .utils import load_credentials, get_resy_headers, get_venue_availability
from .resy_client.models import ResyConfig, TimedReservationRequest
from .resy_client.manager import ResyManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def calendar(req: Request):
    """
    GET /calendar?id=<venue_id>&partySize=<party_size>&userId=<user_id>
    Get restaurant availability calendar
    Query parameters:
    - id: Venue ID (required)
    - partySize: Party size (default: 2)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
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

        # Get party size from query params (default to 2)
        party_size = req.args.get('partySize', '2')

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
            return {
                'success': False,
                'error': f'API returned status {response.status_code}'
            }, 500

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
                'soldOut': reservation_status in ('sold-out', 'not available'),
                'closed': reservation_status == 'closed'
            })

        return {
            'success': True,
            'data': {
                'availability': availability,
                'startDate': today.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }
        }

    except Exception as e:
        logger.error("Error fetching calendar: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def reservation(req: Request):
    """
    POST /reservation
    Create a reservation request
    Body should include:
    - venueId: Venue ID
    - partySize: Party size
    - date: Reservation date (YYYY-MM-DD)
    - hour: Hour (0-23)
    - minute: Minute (0-59)
    - windowHours: Time window in hours (optional, default: 1)
    - seatingType: Seating type preference (optional)
    - dropHour: Drop hour when reservations open (optional, default: 9)
    - dropMinute: Drop minute when reservations open (optional, default: 0)
    Query parameters:
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        data = req.get_json(silent=True) or {}
        user_id = req.args.get('userId')

        # Validate required fields
        required_fields = ['venueId', 'partySize', 'date', 'hour', 'minute']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return {
                'success': False,
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }, 400

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        credentials = load_credentials(user_id)
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

        return {
            'success': True,
            'message': 'Reservation request submitted successfully',
            'resy_token': resy_token
        }

    except Exception as e:
        logger.error("Error making reservation: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def slots(req: Request):
    """
    GET /slots?venueId=<venue_id>&date=<date>&partySize=<party_size>&userId=<user_id>
    Get available time slots for a specific venue and date
    Query parameters:
    - venueId: Venue ID (required)
    - date: Date in YYYY-MM-DD format (required)
    - partySize: Party size (default: 2)
    - userId: User ID (optional) - if provided, loads credentials from Firestore
    """
    try:
        venue_id = req.args.get('venueId')
        date_str = req.args.get('date')
        user_id = req.args.get('userId')

        logger.info(
            f"[SLOTS] Request received: venueId={venue_id}, date={date_str}, "
            f"userId={user_id}, partySize={req.args.get('partySize', '2')}"
        )

        if not venue_id:
            return {
                'success': False,
                'error': 'Missing venueId parameter'
            }, 400

        if not date_str:
            return {
                'success': False,
                'error': 'Missing date parameter'
            }, 400

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)

        # Get party size from query params (default to 2)
        party_size = req.args.get('partySize', '2')

        # Fetch availability using the existing utility function
        availability_data = get_venue_availability(
            venue_id=venue_id,
            day=date_str,
            party_size=party_size,
            config=config
        )

        return {
            'success': True,
            'data': {
                'times': availability_data.get('times', []),
                'status': availability_data.get('status')
            }
        }

    except Exception as e:
        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'error_args': getattr(e, 'args', None),
            'venue_id': venue_id,
            'date': date_str,
            'user_id': user_id,
            'party_size': req.args.get('partySize', '2'),
        }
        logger.error("Error fetching slots: %s", error_details)
        logger.error("Full traceback:\n%s", traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }, 500
