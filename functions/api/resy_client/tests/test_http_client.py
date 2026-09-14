"""
Tests for ResyHttpClient - centralized HTTP transport.

Covers: 429 -> RateLimitError, 401/403 -> ResyAuthError, 500/502 -> ResyTransientError,
and success path.
"""
import pytest
import responses

from resy_client.http_client import ResyHttpClient, REQUEST_TIMEOUT
from resy_client.errors import (
    RateLimitError,
    ResyAuthError,
    ResyInvalidCredentialsError,
    ResySessionExpiredError,
    ResyTransientError,
    ResyApiError,
)
from resy_client.constants import ResyEndpoints
from resy_client.models import ResyConfig


@pytest.fixture
def resy_config():
    """Minimal config for HTTP client."""
    return ResyConfig(
        api_key="test_api_key",
        token="test_token",
        payment_method_id=12345,
    )


@responses.activate
def test_get_success(resy_config):
    """GET with 200 returns response."""
    responses.add(
        responses.GET,
        "https://api.resy.com/3/venue",
        json={"name": "Test Venue"},
        status=200,
    )
    client = ResyHttpClient.build(resy_config)
    resp = client.get("/3/venue", params={"id": "123"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Venue"


@responses.activate
def test_get_429_raises_rate_limit_error(resy_config):
    """GET with 429 raises RateLimitError with retry_after."""
    responses.add(
        responses.GET,
        "https://api.resy.com/3/venue",
        body="Too Many Requests",
        status=429,
        headers={"Retry-After": "2"},
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(RateLimitError) as exc_info:
        client.get("/3/venue", params={"id": "123"})
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 2.0
    assert exc_info.value.endpoint == "/3/venue"
    assert "Too Many Requests" in (exc_info.value.response_body or "")


@responses.activate
def test_get_401_raises_auth_error(resy_config):
    """GET with 401 raises ResyAuthError."""
    responses.add(
        responses.GET,
        "https://api.resy.com/3/venue",
        body="Unauthorized",
        status=401,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyAuthError) as exc_info:
        client.get("/3/venue", params={"id": "123"})
    assert exc_info.value.status_code == 401
    assert exc_info.value.endpoint == "/3/venue"


@responses.activate
def test_419_on_login_raises_invalid_credentials(resy_config):
    """419 on /4/auth/password means the password is wrong -> ResyInvalidCredentialsError.

    Resy returns an identical 419 "Unauthorized" body for both a wrong login and an
    expired token; only the endpoint tells them apart. This is the login case.
    """
    responses.add(
        responses.POST,
        "https://api.resy.com" + ResyEndpoints.PASSWORD_AUTH.value,
        json={"status": 419, "message": "Unauthorized"},
        status=419,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyInvalidCredentialsError) as exc_info:
        client.post_form(ResyEndpoints.PASSWORD_AUTH.value, data={"email": "a", "password": "b"})
    assert exc_info.value.status_code == 419
    # It must NOT be misclassified as an expired session.
    assert not isinstance(exc_info.value, ResySessionExpiredError)


@responses.activate
def test_419_on_data_endpoint_raises_session_expired(resy_config):
    """419 on a non-login endpoint means the stored token is expired/rejected.

    This is the bug that surfaced as "invalid username or password" on search: the
    same 419 must be read as an expired session (recover by reconnecting), never as
    wrong credentials.
    """
    responses.add(
        responses.POST,
        "https://api.resy.com" + ResyEndpoints.VENUE_SEARCH.value,
        json={"status": 419, "message": "Unauthorized"},
        status=419,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResySessionExpiredError) as exc_info:
        client.post_json(ResyEndpoints.VENUE_SEARCH.value, body={"query": "x"})
    assert exc_info.value.status_code == 419
    assert exc_info.value.endpoint == ResyEndpoints.VENUE_SEARCH.value
    # ResySessionExpiredError is a ResyAuthError so endpoint handlers catch it,
    # but it must not be the login-only invalid-credentials type.
    assert isinstance(exc_info.value, ResyAuthError)
    assert not isinstance(exc_info.value, ResyInvalidCredentialsError)


@responses.activate
def test_get_500_raises_transient_error(resy_config):
    """GET with 500 raises ResyTransientError."""
    responses.add(
        responses.GET,
        "https://api.resy.com/4/venue/calendar",
        body="Internal Server Error",
        status=500,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyTransientError) as exc_info:
        client.get("/4/venue/calendar", params={"venue_id": "1"})
    assert exc_info.value.status_code == 500
    assert exc_info.value.endpoint == "/4/venue/calendar"
    assert exc_info.value.response_body == "Internal Server Error"


@responses.activate
def test_get_502_raises_transient_error(resy_config):
    """GET with 502 raises ResyTransientError."""
    responses.add(
        responses.GET,
        "https://api.resy.com/4/find",
        body="Bad Gateway",
        status=502,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyTransientError) as exc_info:
        client.get("/4/find")
    assert exc_info.value.status_code == 502


@responses.activate
def test_get_404_raises_resy_api_error(resy_config):
    """GET with 404 raises ResyApiError (not transient/auth)."""
    responses.add(
        responses.GET,
        "https://api.resy.com/3/venue",
        body="Not Found",
        status=404,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyApiError) as exc_info:
        client.get("/3/venue", params={"id": "999"})
    assert exc_info.value.status_code == 404
    assert exc_info.value.response_body == "Not Found"


def test_request_timeout_constant():
    """REQUEST_TIMEOUT is (5, 10)."""
    assert REQUEST_TIMEOUT == (5, 10)


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    """Make retry backoff instant so retry tests don't actually wait."""
    monkeypatch.setattr("resy_client.http_client.time.sleep", lambda _s: None)


@responses.activate
def test_transient_500_then_success_is_retried(resy_config):
    """A transient Resy 500 is retried and the eventual 200 is returned.

    This is the core fix: a single flaky /4/venue/calendar 500 (which used to surface
    to the user as a bare 500) must be transparently retried, not propagated.
    """
    url = "https://api.resy.com/4/venue/calendar"
    responses.add(responses.GET, url, body="Internal Server Error", status=500)
    responses.add(responses.GET, url, json={"scheduled": []}, status=200)

    client = ResyHttpClient.build(resy_config)
    resp = client.get("/4/venue/calendar", params={"venue_id": "1"})

    assert resp.status_code == 200
    assert len(responses.calls) == 2  # one failure, one retry that succeeded


@responses.activate
def test_transient_500_exhausts_retries_then_raises(resy_config):
    """When every attempt returns 500, the transport gives up after MAX_RETRY_ATTEMPTS."""
    from resy_client.http_client import MAX_RETRY_ATTEMPTS

    responses.add(
        responses.GET,
        "https://api.resy.com/4/venue/calendar",
        body="Internal Server Error",
        status=500,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyTransientError):
        client.get("/4/venue/calendar", params={"venue_id": "1"})
    assert len(responses.calls) == MAX_RETRY_ATTEMPTS


@responses.activate
def test_rate_limit_then_success_is_retried(resy_config):
    """A 429 is retried (honoring the transport backoff) and then succeeds."""
    url = "https://api.resy.com/3/venuesearch/search"
    responses.add(responses.POST, url, body="Too Many Requests", status=429)
    responses.add(responses.POST, url, json={"search": {"hits": []}}, status=200)

    client = ResyHttpClient.build(resy_config)
    resp = client.post_json("/3/venuesearch/search", body={"query": "x"})

    assert resp.status_code == 200
    assert len(responses.calls) == 2


@responses.activate
def test_book_endpoint_is_never_retried(resy_config):
    """Booking is a mutation, so a 500 must NOT be retried -- a retry could create a
    duplicate reservation. It fails fast after a single attempt."""
    responses.add(
        responses.POST,
        "https://api.resy.com" + ResyEndpoints.BOOK.value,
        body="Internal Server Error",
        status=500,
    )
    client = ResyHttpClient.build(resy_config)
    with pytest.raises(ResyTransientError):
        client.post_form(ResyEndpoints.BOOK.value, data={"book_token": "t"})
    assert len(responses.calls) == 1  # no retry for the booking endpoint
