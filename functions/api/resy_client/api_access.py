from datetime import datetime
from requests import Session, HTTPError
from typing import Dict, List
import logging

from .constants import RESY_BASE_URL, ResyEndpoints
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

        resp = self.session.get(search_url, params={"query": query})

        if not resp.ok:
            raise HTTPError(f"Failed to search venues: {resp.status_code}, {resp.text}")

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
        )

        if not resp.ok:
            raise HTTPError(f"Failed to get auth: {resp.status_code}, {resp.text}")

        return AuthResponseBody(**resp.json())

    def find_booking_slots(self, params: FindRequestBody) -> List[Slot]:
        find_url = RESY_BASE_URL + ResyEndpoints.FIND.value

        logger.info(
            f"{datetime.now().isoformat()} Sending request to find booking slots"
        )

        resp = self.session.get(find_url, params=params.model_dump())

        logger.info(f"{datetime.now().isoformat()} Received response for ")

        if not resp.ok:
            raise HTTPError(
                f"Failed to find booking slots: {resp.status_code}, {resp.text}"
            )

        parsed_resp = FindResponseBody(**resp.json())

        if parsed_resp.results and parsed_resp.results.venues:
            return parsed_resp.results.venues[0].slots
        return []

    def get_booking_token(self, params: DetailsRequestBody) -> DetailsResponseBody:
        details_url = RESY_BASE_URL + ResyEndpoints.DETAILS.value

        resp = self.session.get(details_url, params=params.model_dump())

        if not resp.ok:
            raise HTTPError(
                f"Failed to get selected slot details: {resp.status_code}, {resp.text}"
            )

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
        )

        if not resp.ok:
            raise HTTPError(f"Failed to book slot: {resp.status_code}, {resp.text}")

        logger.info(resp.json())
        parsed_resp = BookResponseBody(**resp.json())

        return parsed_resp.resy_token
