from requests import Session
from typing import Dict, List
import logging

from .constants import RESY_BASE_URL, ResyEndpoints
from .errors import RateLimitError
from .models import (
    ResyConfig,
    AuthRequestBody,
    AuthResponseBody,
    FindRequestBody,
    FindResponseBody,
    Slot,
    DetailsRequestBody,
    DetailsResponseBody,
    BookRequestBody,
    BookResponseBody,
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def _check_rate_limit(resp) -> None:
    """Check if response is a rate limit error and raise RateLimitError if so."""
    if resp.status_code == 429:
        # Try to get retry-after header if available
        retry_after = resp.headers.get('Retry-After')
        retry_seconds = float(retry_after) if retry_after else None
        logger.warning(f"Rate limited by Resy API (429). Retry-After: {retry_after}")
        raise RateLimitError(
            f"Rate limit exceeded: {resp.text[:200] if resp.text else 'No details'}",
            retry_after=retry_seconds
        )

# Timeout in seconds for API requests (connect timeout, read timeout)
# Keep these aggressive for time-sensitive snipes
REQUEST_TIMEOUT = (5, 10)  # 5s connect, 10s read


def build_session(config: ResyConfig) -> Session:
    session = Session()
    headers = {
        "Authorization": config.get_authorization(),
        "X-Resy-Auth-Token": config.token,
        "X-Resy-Universal-Auth": config.token,
        "Origin": "https://resy.com",
        "X-origin": "https://resy.com",
        "Referer": "https://resy.com/",
        "Referrer": "https://resy.com/",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    session.headers.update(headers)

    return session


class ResyApiAccess:
    @classmethod
    def build(cls, config: ResyConfig) -> "ResyApiAccess":
        session = build_session(config)
        return cls(session)

    def __init__(self, session: Session):
        self.session = session

    def search_venues(self, query: str) -> List[Dict]:
        """
        Search for venues by name

        Args:
            query: Restaurant name search query

        Returns:
            List of venue dictionaries with id, name, location info
        """
        search_url = RESY_BASE_URL + ResyEndpoints.VENUE_SEARCH.value

        resp = self.session.get(search_url, params={"query": query}, timeout=REQUEST_TIMEOUT)

        if not resp.ok:
            resp.raise_for_status()  # This properly attaches response to HTTPError

        data = resp.json()

        # Extract venue results
        results = []
        if "search" in data and "hits" in data["search"]:
            for hit in data["search"]["hits"]:
                venue = hit.get("_source", {})
                results.append({
                    "id": venue.get("id", {}).get("resy"),
                    "name": venue.get("name"),
                    "locality": venue.get("locality"),
                    "region": venue.get("region"),
                    "neighborhood": venue.get("neighborhood"),
                    "type": venue.get("type"),
                    "price_range": venue.get("price_range_id", 0),
                })

        return results

    def auth(self, body: AuthRequestBody) -> AuthResponseBody:
        auth_url = RESY_BASE_URL + ResyEndpoints.PASSWORD_AUTH.value

        resp = self.session.post(
            auth_url,
            data=body.model_dump(),
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=REQUEST_TIMEOUT,
        )

        if not resp.ok:
            resp.raise_for_status()

        return AuthResponseBody(**resp.json())

    def find_booking_slots(self, params: FindRequestBody) -> List[Slot]:
        find_url = RESY_BASE_URL + ResyEndpoints.FIND.value

        logger.info("Sending request to find booking slots with params: %s", params.model_dump())

        resp = self.session.get(find_url, params=params.model_dump(), timeout=REQUEST_TIMEOUT)

        logger.info(f"Received response from find booking slots: {resp.text}")

        if not resp.ok:
            _check_rate_limit(resp)  # Check for 429 before generic error
            resp.raise_for_status()

        parsed_resp = FindResponseBody(**resp.json())

        if parsed_resp.results and parsed_resp.results.venues:
            return parsed_resp.results.venues[0].slots
        return []

    def get_booking_token(self, params: DetailsRequestBody) -> DetailsResponseBody:
        details_url = RESY_BASE_URL + ResyEndpoints.DETAILS.value

        resp = self.session.get(details_url, params=params.model_dump(), timeout=REQUEST_TIMEOUT)

        if not resp.ok:
            _check_rate_limit(resp)  # Check for 429 before generic error
            resp.raise_for_status()

        return DetailsResponseBody(**resp.json())

    def _dump_book_request_body_to_dict(self, body: BookRequestBody) -> Dict:
        """
        requests lib doesn't urlencode nested dictionaries,
        so dump struct_payment_method to json and slot that in the dict
        """
        payment_method = body.struct_payment_method.model_dump_json().replace(" ", "")
        body_dict = body.model_dump()
        body_dict["struct_payment_method"] = payment_method
        return body_dict

    def book_slot(self, body: BookRequestBody) -> str:
        book_url = RESY_BASE_URL + ResyEndpoints.BOOK.value

        body_dict = self._dump_book_request_body_to_dict(body)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://widgets.resy.com",
            "X-Origin": "https://widgets.resy.com",
            "Referrer": "https://widgets.resy.com/",
            "Cache-Control": "no-cache",
        }

        resp = self.session.post(
            book_url,
            data=body_dict,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if not resp.ok:
            _check_rate_limit(resp)  # Check for 429 before generic error
            resp.raise_for_status()

        logger.info(resp.json())
        parsed_resp = BookResponseBody(**resp.json())

        return parsed_resp.resy_token
