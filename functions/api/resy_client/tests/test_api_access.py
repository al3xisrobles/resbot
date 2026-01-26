"""
Tests for ResyApiAccess - HTTP API interaction layer.

Tests cover:
- All API endpoints (search, auth, find, details, book)
- Success scenarios
- Error handling (HTTP errors, timeouts, connection errors)
- Response parsing
- Request formatting
"""
import pytest
import responses
from requests.exceptions import HTTPError
from datetime import datetime

from resy_client.api_access import ResyApiAccess, build_session, REQUEST_TIMEOUT
from resy_client.models import (
    AuthRequestBody,
    FindRequestBody,
    DetailsRequestBody,
    BookRequestBody,
    PaymentMethod,
)
from resy_client.constants import RESY_BASE_URL, ResyEndpoints
from resy_client.errors import RateLimitError


class TestBuildSession:
    """Tests for session builder function."""

    def test_build_session_sets_authorization_header(self, resy_config):
        """Session should include Authorization header with API key."""
        session = build_session(resy_config)
        assert "Authorization" in session.headers
        assert resy_config.api_key in session.headers["Authorization"]

    def test_build_session_sets_auth_tokens(self, resy_config):
        """Session should include both auth token headers."""
        session = build_session(resy_config)
        assert session.headers["X-Resy-Auth-Token"] == resy_config.token
        assert session.headers["X-Resy-Universal-Auth"] == resy_config.token

    def test_build_session_sets_origin_headers(self, resy_config):
        """Session should include proper origin headers for Resy."""
        session = build_session(resy_config)
        assert session.headers["Origin"] == "https://resy.com"
        assert session.headers["Referer"] == "https://resy.com/"

    def test_build_session_sets_user_agent(self, resy_config):
        """Session should include a browser-like User-Agent."""
        session = build_session(resy_config)
        assert "Mozilla" in session.headers["User-Agent"]
        assert "Chrome" in session.headers["User-Agent"]


class TestResyApiAccessBuild:
    """Tests for ResyApiAccess factory method."""

    def test_build_creates_instance_with_configured_session(self, resy_config):
        """Build should create instance with properly configured session."""
        api = ResyApiAccess.build(resy_config)
        assert isinstance(api, ResyApiAccess)
        assert api.session is not None
        assert resy_config.token in api.session.headers["X-Resy-Auth-Token"]


class TestSearchVenues:
    """Tests for venue search endpoint."""

    @responses.activate
    def test_search_venues_returns_results(self, resy_config, venue_search_response):
        """Search should return list of venues matching query."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.VENUE_SEARCH.value}",
            json=venue_search_response,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        results = api.search_venues("Carbone")

        assert len(results) == 2
        assert results[0]["name"] == "Carbone"
        assert results[0]["id"] == 60058
        assert results[0]["locality"] == "New York"

    @responses.activate
    def test_search_venues_empty_results(self, resy_config):
        """Search with no matches should return empty list."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.VENUE_SEARCH.value}",
            json={"search": {"hits": []}},
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        results = api.search_venues("NonexistentRestaurant12345")

        assert results == []

    @responses.activate
    def test_search_venues_missing_search_key(self, resy_config):
        """Search with malformed response should return empty list."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.VENUE_SEARCH.value}",
            json={},
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        results = api.search_venues("Carbone")

        assert results == []

    @responses.activate
    def test_search_venues_http_error(self, resy_config):
        """Search should raise HTTPError on server error."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.VENUE_SEARCH.value}",
            json={"error": "Internal Server Error"},
            status=500,
        )

        api = ResyApiAccess.build(resy_config)

        with pytest.raises(HTTPError):
            api.search_venues("Carbone")

    @responses.activate
    def test_search_venues_unauthorized(self, resy_config):
        """Search should raise HTTPError on 401 unauthorized."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.VENUE_SEARCH.value}",
            json={"error": "Unauthorized"},
            status=401,
        )

        api = ResyApiAccess.build(resy_config)

        with pytest.raises(HTTPError) as exc_info:
            api.search_venues("Carbone")

        assert exc_info.value.response.status_code == 401


class TestAuth:
    """Tests for authentication endpoint."""

    @responses.activate
    def test_auth_success(self, resy_config):
        """Auth should return token and payment methods on success."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.PASSWORD_AUTH.value}",
            json={
                "token": "new_auth_token_12345",
                "payment_methods": [{"id": 99999}],
            },
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        body = AuthRequestBody(email="test@example.com", password="password123")
        result = api.auth(body)

        assert result.token == "new_auth_token_12345"
        assert len(result.payment_methods) == 1
        assert result.payment_methods[0].id == 99999

    @responses.activate
    def test_auth_invalid_credentials(self, resy_config):
        """Auth should raise HTTPError on invalid credentials."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.PASSWORD_AUTH.value}",
            json={"error": "Invalid email or password"},
            status=401,
        )

        api = ResyApiAccess.build(resy_config)
        body = AuthRequestBody(email="wrong@example.com", password="wrongpassword")

        with pytest.raises(HTTPError) as exc_info:
            api.auth(body)

        assert exc_info.value.response.status_code == 401

    @responses.activate
    def test_auth_sends_form_data(self, resy_config):
        """Auth should send credentials as form-urlencoded data."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.PASSWORD_AUTH.value}",
            json={"token": "token", "payment_methods": []},
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        body = AuthRequestBody(email="test@example.com", password="password123")
        api.auth(body)

        # Verify request was made with form data
        assert len(responses.calls) == 1
        assert "email=test%40example.com" in responses.calls[0].request.body


class TestFindBookingSlots:
    """Tests for finding available booking slots."""

    @responses.activate
    def test_find_slots_returns_slot_list(self, resy_config, find_response_with_slots):
        """Find should return list of Slot objects."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=find_response_with_slots,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        slots = api.find_booking_slots(params)

        assert len(slots) > 0
        assert all(hasattr(s, "config") for s in slots)
        assert all(hasattr(s, "date") for s in slots)

    @responses.activate
    def test_find_slots_empty_venue(self, resy_config, find_response_empty):
        """Find should return empty list when no slots available."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=find_response_empty,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        slots = api.find_booking_slots(params)

        assert slots == []

    @responses.activate
    def test_find_slots_no_venues_in_response(self, resy_config):
        """Find should return empty list when venues array is empty."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json={"results": {"venues": []}},
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        slots = api.find_booking_slots(params)

        assert slots == []

    @responses.activate
    def test_find_slots_sends_correct_params(self, resy_config, find_response_empty):
        """Find should send venue_id, party_size, and day as query params."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=find_response_empty,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        api.find_booking_slots(params)

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "venue_id=60058" in request.url
        assert "party_size=2" in request.url
        assert "day=2026-02-14" in request.url

    @responses.activate
    def test_find_slots_http_error(self, resy_config):
        """Find should raise HTTPError on server error (non-429)."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json={"error": "Internal Server Error"},
            status=500,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")

        with pytest.raises(HTTPError) as exc_info:
            api.find_booking_slots(params)

        assert exc_info.value.response.status_code == 500

    @responses.activate
    def test_find_slots_rate_limit_raises_rate_limit_error(self, resy_config):
        """Find should raise RateLimitError (not HTTPError) on 429."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json={"status": 429, "message": "Rate Limit Exceeded"},
            status=429,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")

        with pytest.raises(RateLimitError) as exc_info:
            api.find_booking_slots(params)

        assert "Rate limit exceeded" in str(exc_info.value)

    @responses.activate
    def test_find_slots_rate_limit_with_retry_after_header(self, resy_config):
        """Find should capture Retry-After header from 429 response."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json={"status": 429, "message": "Rate Limit Exceeded"},
            status=429,
            headers={"Retry-After": "5"},
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")

        with pytest.raises(RateLimitError) as exc_info:
            api.find_booking_slots(params)

        assert exc_info.value.retry_after == 5.0

    @responses.activate
    def test_find_slots_parses_slot_times_correctly(self, resy_config):
        """Find should correctly parse slot start/end times."""
        slot_response = {
            "results": {
                "venues": [
                    {
                        "slots": [
                            {
                                "config": {"id": 123, "type": "Dining", "token": "test_token"},
                                "date": {
                                    "start": "2026-02-14T19:30:00",
                                    "end": "2026-02-14T21:15:00",
                                },
                            }
                        ]
                    }
                ]
            }
        }
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=slot_response,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        slots = api.find_booking_slots(params)

        assert len(slots) == 1
        assert slots[0].date.start.hour == 19
        assert slots[0].date.start.minute == 30
        assert slots[0].date.end.hour == 21
        assert slots[0].date.end.minute == 15


class TestGetBookingToken:
    """Tests for getting booking token (details endpoint)."""

    @responses.activate
    def test_get_token_success(self, resy_config, details_response):
        """Get token should return DetailsResponseBody with book_token."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=details_response,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = DetailsRequestBody(
            config_id="test_config_token",
            party_size=2,
            day="2026-02-14",
        )
        result = api.get_booking_token(params)

        assert result.book_token.value == "test_book_token_value_12345"
        assert isinstance(result.book_token.date_expires, datetime)

    @responses.activate
    def test_get_token_sends_correct_params(self, resy_config, details_response):
        """Get token should send config_id, party_size, and day."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json=details_response,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = DetailsRequestBody(
            config_id="rgs://resy/60058/4069767/2/2026-02-14",
            party_size=2,
            day="2026-02-14",
        )
        api.get_booking_token(params)

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "config_id=" in request.url
        assert "party_size=2" in request.url
        assert "day=2026-02-14" in request.url

    @responses.activate
    def test_get_token_slot_already_taken(self, resy_config):
        """Get token should raise HTTPError when slot is taken."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json={"error": "Slot no longer available"},
            status=410,  # Gone
        )

        api = ResyApiAccess.build(resy_config)
        params = DetailsRequestBody(
            config_id="test_config_token",
            party_size=2,
            day="2026-02-14",
        )

        with pytest.raises(HTTPError) as exc_info:
            api.get_booking_token(params)

        assert exc_info.value.response.status_code == 410

    @responses.activate
    def test_get_token_rate_limit_raises_rate_limit_error(self, resy_config):
        """Get token should raise RateLimitError on 429."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.DETAILS.value}",
            json={"status": 429, "message": "Rate Limit Exceeded"},
            status=429,
        )

        api = ResyApiAccess.build(resy_config)
        params = DetailsRequestBody(
            config_id="test_config_token",
            party_size=2,
            day="2026-02-14",
        )

        with pytest.raises(RateLimitError):
            api.get_booking_token(params)


class TestBookSlot:
    """Tests for booking a slot."""

    @responses.activate
    def test_book_slot_success(self, resy_config, book_response_success):
        """Book should return resy_token on success."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=book_response_success,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )
        token = api.book_slot(body)

        assert token == "resy_confirmation_token_abc123"

    @responses.activate
    def test_book_slot_sends_form_data(self, resy_config, book_response_success):
        """Book should send data as form-urlencoded."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=book_response_success,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )
        api.book_slot(body)

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "book_token=test_book_token" in request.body

    @responses.activate
    def test_book_slot_sets_widget_origin(self, resy_config, book_response_success):
        """Book should use widgets.resy.com as origin."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json=book_response_success,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )
        api.book_slot(body)

        request = responses.calls[0].request
        assert request.headers["Origin"] == "https://widgets.resy.com"

    @responses.activate
    def test_book_slot_already_taken(self, resy_config):
        """Book should raise HTTPError when slot is already taken."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "This reservation is no longer available"},
            status=412,  # Precondition Failed
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )

        with pytest.raises(HTTPError) as exc_info:
            api.book_slot(body)

        assert exc_info.value.response.status_code == 412
        # Verify response is properly attached (the bug we fixed)
        assert exc_info.value.response is not None

    @responses.activate
    def test_book_slot_payment_declined(self, resy_config):
        """Book should raise HTTPError when payment is declined."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "Payment method declined"},
            status=402,  # Payment Required
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )

        with pytest.raises(HTTPError) as exc_info:
            api.book_slot(body)

        assert exc_info.value.response.status_code == 402

    @responses.activate
    def test_book_slot_server_error(self, resy_config):
        """Book should raise HTTPError on 500 server error."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"error": "Internal Server Error"},
            status=500,
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )

        with pytest.raises(HTTPError) as exc_info:
            api.book_slot(body)

        assert exc_info.value.response.status_code == 500

    @responses.activate
    def test_book_slot_rate_limit_raises_rate_limit_error(self, resy_config):
        """Book should raise RateLimitError on 429."""
        responses.add(
            responses.POST,
            f"{RESY_BASE_URL}{ResyEndpoints.BOOK.value}",
            json={"status": 429, "message": "Rate Limit Exceeded"},
            status=429,
        )

        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_book_token",
            struct_payment_method=PaymentMethod(id=12345),
        )

        with pytest.raises(RateLimitError):
            api.book_slot(body)


class TestTimeouts:
    """Tests for request timeout handling."""

    @responses.activate
    def test_find_slots_uses_timeout(self, resy_config, find_response_empty):
        """API calls should use configured timeout."""
        responses.add(
            responses.GET,
            f"{RESY_BASE_URL}{ResyEndpoints.FIND.value}",
            json=find_response_empty,
            status=200,
        )

        api = ResyApiAccess.build(resy_config)
        params = FindRequestBody(venue_id="60058", party_size=2, day="2026-02-14")
        api.find_booking_slots(params)

        # Verify timeout constant is defined correctly
        assert REQUEST_TIMEOUT == (5, 10)


class TestDumpBookRequestBody:
    """Tests for the internal method that formats book request body."""

    def test_dump_serializes_payment_method_as_json(self, resy_config):
        """Payment method should be serialized as JSON string."""
        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_token",
            struct_payment_method=PaymentMethod(id=12345),
        )

        result = api._dump_book_request_body_to_dict(body)

        # struct_payment_method should be a JSON string, not a dict
        assert isinstance(result["struct_payment_method"], str)
        assert '"id":12345' in result["struct_payment_method"]

    def test_dump_includes_all_fields(self, resy_config):
        """Dumped dict should include all request body fields."""
        api = ResyApiAccess.build(resy_config)
        body = BookRequestBody(
            book_token="test_token",
            struct_payment_method=PaymentMethod(id=12345),
            source_id="custom_source",
        )

        result = api._dump_book_request_body_to_dict(body)

        assert "book_token" in result
        assert "struct_payment_method" in result
        assert "source_id" in result
        assert result["book_token"] == "test_token"
        assert result["source_id"] == "custom_source"
