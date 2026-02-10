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
    ResyTransientError,
    ResyApiError,
)
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
