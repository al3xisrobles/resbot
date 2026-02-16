import logging
from typing import Dict, List, Optional

from pydantic import ValidationError

from .constants import ResyEndpoints
from .errors import ResyApiError
from .http_client import REQUEST_TIMEOUT, ResyHttpClient
from .models import (
    AuthRequestBody,
    AuthResponseBody,
    BookRequestBody,
    BookResponseBody,
    CalendarRequestParams,
    CalendarResponseBody,
    CityListResponseBody,
    DetailsRequestBody,
    DetailsResponseBody,
    FindRequestBody,
    FindResponseBody,
    ResyConfig,
    Slot,
    Venue,
    VenueResponseBody,
    VenueSearchRequestBody,
    VenueSearchResponseBody,
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def _parse_json_or_raise(resp, model_class, endpoint: str):
    """Parse response JSON into Pydantic model; on ValidationError raise ResyApiError with body."""
    try:
        data = resp.json()
    except ValueError as e:
        raise ResyApiError(
            f"Invalid JSON from {endpoint}: {e}",
            status_code=resp.status_code,
            response_body=resp.text,
            endpoint=endpoint,
        ) from e
    try:
        return model_class(**data)
    except ValidationError as e:
        raise ResyApiError(
            f"Response schema mismatch for {endpoint}: {e}",
            status_code=resp.status_code,
            response_body=resp.text,
            endpoint=endpoint,
        ) from e


class ResyApiAccess:
    @classmethod
    def build(cls, config: ResyConfig) -> "ResyApiAccess":
        client = ResyHttpClient.build(config)
        return cls(client)

    def __init__(self, client: ResyHttpClient):
        self.client = client

    def search_venues(self, query: str) -> List[Dict]:
        """
        Search for venues by name (GET with query param).

        Args:
            query: Restaurant name search query

        Returns:
            List of venue dictionaries with id, name, location info
        """
        resp = self.client.get(
            ResyEndpoints.VENUE_SEARCH.value,
            params={"query": query},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
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

    def search_venues_advanced(self, body: VenueSearchRequestBody) -> VenueSearchResponseBody:
        """
        Search venues with full POST body (geo, filters, pagination).

        Args:
            body: VenueSearchRequestBody

        Returns:
            VenueSearchResponseBody with search.hits and meta.total
        """
        endpoint = ResyEndpoints.VENUE_SEARCH.value
        resp = self.client.post_json(
            endpoint,
            body=body.model_dump(exclude_none=True),
            timeout=(5, 30),
        )
        return _parse_json_or_raise(resp, VenueSearchResponseBody, endpoint)

    def auth(self, body: AuthRequestBody) -> AuthResponseBody:
        """Authenticate with Resy using /4/auth/password. Returns token and payment methods."""
        endpoint = ResyEndpoints.PASSWORD_AUTH.value
        resp = self.client.post_form(
            endpoint,
            data=body.model_dump(),
            extra_headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=REQUEST_TIMEOUT,
        )
        return _parse_json_or_raise(resp, AuthResponseBody, endpoint)

    def find_booking_slots(self, params: FindRequestBody) -> List[Slot]:
        venue = self.find_venue_result(params)
        return venue.slots if venue else []

    def find_venue_result(self, params: FindRequestBody) -> Optional[Venue]:
        """POST /4/find; returns first venue (slots + templates) or None."""
        endpoint = ResyEndpoints.FIND.value
        logger.info("Sending request to find booking slots with params: %s", params.model_dump())
        resp = self.client.post_json(
            endpoint,
            body=params.model_dump(),
            timeout=REQUEST_TIMEOUT,
        )
        logger.info("Received response from find booking slots: %s", resp.text)
        parsed = _parse_json_or_raise(resp, FindResponseBody, endpoint)
        if parsed.results and parsed.results.venues:
            return parsed.results.venues[0]
        return None

    def get_booking_token(self, params: DetailsRequestBody) -> DetailsResponseBody:
        endpoint = ResyEndpoints.DETAILS.value
        resp = self.client.get(
            endpoint,
            params=params.model_dump(),
            timeout=REQUEST_TIMEOUT,
        )
        return _parse_json_or_raise(resp, DetailsResponseBody, endpoint)

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
        endpoint = ResyEndpoints.BOOK.value
        body_dict = self._dump_book_request_body_to_dict(body)
        extra_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://widgets.resy.com",
            "X-Origin": "https://widgets.resy.com",
            "Referrer": "https://widgets.resy.com/",
            "Cache-Control": "no-cache",
        }
        resp = self.client.post_form(
            endpoint,
            data=body_dict,
            extra_headers=extra_headers,
            timeout=REQUEST_TIMEOUT,
        )
        logger.info("%s", resp.json())
        parsed = _parse_json_or_raise(resp, BookResponseBody, endpoint)
        return parsed.resy_token

    def get_calendar(self, params: CalendarRequestParams) -> CalendarResponseBody:
        """GET /4/venue/calendar. Returns scheduled dates with inventory/reservation status."""
        endpoint = ResyEndpoints.CALENDAR.value
        resp = self.client.get(
            endpoint,
            params=params.model_dump(),
            timeout=REQUEST_TIMEOUT,
        )
        return _parse_json_or_raise(resp, CalendarResponseBody, endpoint)

    def get_venue(self, venue_id: str) -> VenueResponseBody:
        """GET /3/venue. Returns venue details (name, location, images, etc.)."""
        endpoint = ResyEndpoints.VENUE.value
        resp = self.client.get(
            endpoint,
            params={"id": venue_id},
            timeout=(5, 30),
        )
        return _parse_json_or_raise(resp, VenueResponseBody, endpoint)

    def get_city_list(
        self,
        slug: str,
        list_type: str,
        limit: int = 10,
    ) -> CityListResponseBody:
        """GET /3/cities/{slug}/list/{list_type}. E.g. slug='new-york-ny', list_type='climbing'."""
        path = ResyEndpoints.CITY_LIST.value.replace("{slug}", slug).replace("{list_type}", list_type)
        resp = self.client.get(
            path,
            params={"limit": limit},
            timeout=REQUEST_TIMEOUT,
        )
        return _parse_json_or_raise(resp, CityListResponseBody, path)


def build_resy_client(config: dict | ResyConfig) -> ResyApiAccess:
    """One-liner to build a ready-to-use API client from credentials dict or ResyConfig."""
    if isinstance(config, dict):
        config = ResyConfig(**config)
    return ResyApiAccess.build(config)
