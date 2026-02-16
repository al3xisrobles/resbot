"""
User session data endpoint
Returns onboarding status and Resy account information
"""

import logging
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import firestore

from .sentry_utils import with_sentry_trace
from .response_schemas import success_response, error_response, MeData, ResyUserData

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
@with_sentry_trace
def me(req: Request):
    """
    GET /me?userId=<user_id>
    Returns user session data including onboarding status
    
    Response:
    {
        "onboardingStatus": "not_started" | "completed",
        "hasPaymentMethod": boolean,
        "resy": {
            "email": string,
            "firstName": string,
            "lastName": string,
            "paymentMethodId": number | null
        } | null
    }
    """
    try:
        firebase_uid = req.args.get('userId')
        if not firebase_uid:
            return error_response('userId is required', 400)

        db = firestore.client()
        doc_ref = db.collection('resyCredentials').document(firebase_uid)

        # Check if credentials exist
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            payment_method_id = data.get('paymentMethodId')
            has_payment_method = payment_method_id is not None

            return success_response(
                MeData(
                    onboardingStatus='completed',
                    hasPaymentMethod=has_payment_method,
                    resy=ResyUserData(
                        email=data.get('email', ''),
                        firstName=data.get('firstName', ''),
                        lastName=data.get('lastName', ''),
                        paymentMethodId=payment_method_id
                    )
                )
            )

        # No credentials found - user hasn't onboarded
        return success_response(
            MeData(
                onboardingStatus='not_started',
                hasPaymentMethod=False,
                resy=None
            )
        )

    except Exception as e:
        logger.error("Error in /me endpoint: %s", e)
        return error_response(str(e), 500)
