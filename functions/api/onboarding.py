"""
Resy Account Onboarding Cloud Function
Handles direct API authentication with Resy
"""

import logging
import os
import traceback
from urllib.parse import urlencode

import requests
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import firestore
from google.cloud import firestore as gc_firestore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Static Resy API key - constant for all users
RESY_API_KEY = os.getenv("RESY_API_KEY", "VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5")


def authenticate_with_resy(email: str, password: str) -> dict:
    """
    Authenticate with Resy API using email and password.

    Args:
        email: User's Resy email
        password: User's Resy password (will NOT be stored)

    Returns:
        dict: Response data from Resy API

    Raises:
        Exception: If authentication fails
    """
    url = "https://api.resy.com/4/auth/password"

    headers = {
        "authorization": f'ResyAPI api_key="{RESY_API_KEY}"',
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json, text/plain, */*",
        "origin": "https://resy.com",
        "x-origin": "https://resy.com",
    }

    # Form-encoded body - do NOT log this as it contains the password
    body = urlencode({"email": email, "password": password})

    logger.info("Authenticating with Resy for email: %s", email)

    try:
        response = requests.post(url, headers=headers, data=body, timeout=10)

        if response.status_code != 200:
            logger.error("Resy authentication failed with status %s", response.status_code)
            raise Exception("Invalid Resy login")

        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error("Request to Resy API failed: %s", e)
        raise Exception("Failed to connect to Resy") from e


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST"]))
def start_resy_onboarding(req: Request):
    """
    HTTP Cloud Function to authenticate and store Resy credentials

    Expected request body:
    {
        "email": "user@example.com",
        "password": "...",
        "userId": "userId"
    }

    Returns:
    {
        "success": true,
        "hasPaymentMethod": true,
        "paymentMethodId": 123456
    }

    Or on error:
    {
        "success": false,
        "error": "Invalid Resy login"
    }
    """
    try:
        # Parse request body
        request_json = req.get_json(silent=True)
        if not request_json:
            return {
                'success': False,
                'error': 'Invalid request body'
            }, 400

        email = request_json.get('email')
        password = request_json.get('password')
        firebase_uid = request_json.get('userId')

        # Validate required fields
        if not email or not password or not firebase_uid:
            return {
                'success': False,
                'error': 'Missing required fields: email, password, userId'
            }, 400

        logger.info("Starting Resy onboarding for Firebase user: %s", firebase_uid)

        # Authenticate with Resy API
        auth_data = authenticate_with_resy(email, password)

        # Password is now out of scope and will be garbage collected
        # Do NOT log or store the password anywhere

        # Extract payment method info
        payment_methods = auth_data.get('payment_methods', [])
        payment_method_id = auth_data.get('payment_method_id')
        has_payment_method = len(payment_methods) > 0 and payment_method_id is not None

        # Prepare credentials for Firestore
        credentials = {
            'apiKey': RESY_API_KEY,
            'token': auth_data.get('token'),
            'paymentMethodId': payment_method_id,
            'email': auth_data.get('em_address'),
            'firstName': auth_data.get('first_name'),
            'lastName': auth_data.get('last_name'),
            'guestId': auth_data.get('guest_id'),
            'userId': auth_data.get('id'),  # Resy user ID
            'mobileNumber': auth_data.get('mobile_number'),
            'paymentMethods': payment_methods,
            'legacyToken': auth_data.get('legacy_token'),
            'updatedAt': gc_firestore.SERVER_TIMESTAMP
        }

        # Store credentials in Firestore
        db = firestore.client()
        doc_ref = db.collection('resyCredentials').document(firebase_uid)

        try:
            doc_ref.set(credentials)
            logger.info("[ONBOARDING] Firestore write initiated for user %s", firebase_uid)

            # Verify the write succeeded by reading it back
            verify_doc = doc_ref.get()
            if not verify_doc.exists:
                error_msg = (
                    f"Failed to verify Firestore write for user {firebase_uid} - "
                    f"document does not exist after write"
                )
                logger.error("[ONBOARDING] %s", error_msg)
                raise Exception(error_msg)

            logger.info(
                f"✓ Stored Resy credentials for Firebase user {firebase_uid} "
                f"(Resy user: {credentials['userId']}, has payment: {has_payment_method})"
            )
        except Exception as firestore_error:
            error_msg = f"Failed to store credentials in Firestore: {str(firestore_error)}"
            logger.error("[ONBOARDING] %s", error_msg)
            logger.error(f"[ONBOARDING] Full traceback:\n{traceback.format_exc()}")
            raise Exception(error_msg) from firestore_error

        return {
            'success': True,
            'hasPaymentMethod': has_payment_method,
            'paymentMethodId': payment_method_id
        }, 200

    except Exception as e:
        error_message = str(e)
        logger.error("Error during Resy onboarding: %s", error_message)

        # Return appropriate error response
        if "Invalid Resy login" in error_message:
            return {
                'success': False,
                'error': 'Invalid Resy login'
            }, 400
        return {
            'success': False,
            'error': 'Failed to connect Resy account'
        }, 502


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "DELETE"]))
def resy_account(req: Request):
    """
    GET /resy_account?userId=<user_id>
    Get full Resy account credentials including payment methods

    POST /resy_account?userId=<user_id>
    Update selected payment method
    Body: { "paymentMethodId": 123456 }

    DELETE /resy_account?userId=<user_id>
    Disconnect Resy account
    """
    try:
        firebase_uid = req.args.get('userId')
        if not firebase_uid:
            return {
                'success': False,
                'error': 'userId is required'
            }, 400

        db = firestore.client()
        doc_ref = db.collection('resyCredentials').document(firebase_uid)

        if req.method == 'GET':
            # Check if credentials exist
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                # Return full credential details including payment methods
                payment_methods = data.get('paymentMethods', [])
                payment_method_id = data.get('paymentMethodId')
                
                return {
                    'success': True,
                    'connected': True,
                    'hasPaymentMethod': payment_method_id is not None,
                    'paymentMethodId': payment_method_id,
                    'paymentMethods': payment_methods,
                    'email': data.get('email'),
                    'firstName': data.get('firstName', ''),
                    'lastName': data.get('lastName', ''),
                    'name': f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
                    'mobileNumber': data.get('mobileNumber'),
                    'userId': data.get('userId')  # Resy user ID
                }, 200
            return {
                'success': True,
                'connected': False
            }, 200

        if req.method == 'POST':
            # Update payment method
            request_json = req.get_json(silent=True)
            if not request_json:
                return {
                    'success': False,
                    'error': 'Invalid request body'
                }, 400

            payment_method_id = request_json.get('paymentMethodId')
            if payment_method_id is None:
                return {
                    'success': False,
                    'error': 'paymentMethodId is required'
                }, 400

            # Check if credentials exist
            doc = doc_ref.get()
            if not doc.exists:
                return {
                    'success': False,
                    'error': 'Resy account not connected'
                }, 404

            data = doc.to_dict()
            payment_methods = data.get('paymentMethods', [])
            
            # Validate that the payment method exists in the user's payment methods
            payment_method_ids = [pm.get('id') if isinstance(pm, dict) else pm for pm in payment_methods]
            if payment_method_id not in payment_method_ids:
                return {
                    'success': False,
                    'error': 'Payment method not found in user\'s payment methods'
                }, 400

            # Update the payment method ID
            doc_ref.update({
                'paymentMethodId': payment_method_id,
                'updatedAt': gc_firestore.SERVER_TIMESTAMP
            })
            
            logger.info("Updated payment method for Firebase user %s to %s", firebase_uid, payment_method_id)
            return {
                'success': True,
                'message': 'Payment method updated',
                'paymentMethodId': payment_method_id
            }, 200

        if req.method == 'DELETE':
            # Delete credentials
            doc_ref.delete()
            logger.info("Deleted Resy credentials for Firebase user %s", firebase_uid)
            return {
                'success': True,
                'message': 'Resy account disconnected'
            }, 200

    except Exception as e:
        logger.error("Error in resy_account endpoint: %s", e)
        return {
            'success': False,
            'error': str(e)
        }, 500
