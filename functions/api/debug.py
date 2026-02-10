"""
Resy API debug Cloud Function.
Probes Resy endpoints and returns raw responses, schema validation, and timing.
Always returns 200 with a diagnostic payload (errors are included in the payload).
"""

import json
import logging
import os
import time
from datetime import date, timedelta

from firebase_functions.https_fn import Request, on_request
from firebase_functions.options import CorsOptions, MemoryOption
from pydantic import ValidationError

from .resy_client.api_access import build_resy_client
from .resy_client.constants import ResyEndpoints
from .resy_client.http_client import REQUEST_TIMEOUT, ResyHttpClient
from .resy_client.models import (
    AuthRequestBody,
    CalendarResponseBody,
    CityListResponseBody,
    FindResponseBody,
    ResyConfig,
    VenueResponseBody,
    VenueSearchRequestBody,
    VenueSearchResponseBody,
)
from .sentry_utils import with_sentry_trace

logger = logging.getLogger(__name__)

# Default API key (same as utils.py public endpoints)
DEFAULT_API_KEY = "VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"

# Rate-limit header names to include in diagnostics
RATE_LIMIT_HEADERS = ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining")


def _get_debug_credentials():
    """Load debug auth credentials from environment."""
    email = os.getenv("RESY_DEBUG_EMAIL", "").strip()
    password = os.getenv("RESY_DEBUG_PASSWORD", "").strip()
    if not email or not password:
        raise ValueError(
            "RESY_DEBUG_EMAIL and RESY_DEBUG_PASSWORD must be set for the debug endpoint"
        )
    api_key = os.getenv("RESY_API_KEY", DEFAULT_API_KEY)
    return {"email": email, "password": password, "api_key": api_key}


def _auth_and_build_client():
    """
    Authenticate with Resy using debug credentials and return (http_client, token_preview, time_ms).
    """
    creds = _get_debug_credentials()
    config = ResyConfig(
        api_key=creds["api_key"],
        token="",
        payment_method_id=0,
    )
    api_access = build_resy_client(config)
    body = AuthRequestBody(email=creds["email"], password=creds["password"])
    start = time.perf_counter()
    auth_resp = api_access.auth(body)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    token = auth_resp.token or ""
    token_preview = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
    config_with_token = ResyConfig(
        api_key=creds["api_key"],
        token=token,
        payment_method_id=(
            auth_resp.payment_methods[0].id if auth_resp.payment_methods else 0
        ),
    )
    http_client = ResyHttpClient.build(config_with_token)
    return http_client, token_preview, elapsed_ms


def _extract_rate_limit_headers(resp) -> dict:
    """Extract rate-limit-related headers from a response."""
    out = {}
    for name in RATE_LIMIT_HEADERS:
        val = resp.headers.get(name)
        if val is not None:
            out[name] = val
    return out


def _try_parse_json(text: str):
    """Parse JSON or return None and the raw text."""
    if not text or not text.strip():
        return None, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, text


def _validate_calendar(data: dict) -> tuple[bool, str | None]:
    """Validate against CalendarResponseBody. Return (valid, error_message)."""
    try:
        CalendarResponseBody(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def _validate_find(data: dict) -> tuple[bool, str | None]:
    """Validate find response (FindResponseBody). Return (valid, error_message)."""
    try:
        FindResponseBody(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def _validate_venue(data: dict) -> tuple[bool, str | None]:
    """Validate against VenueResponseBody."""
    try:
        VenueResponseBody(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def _validate_venue_search(data: dict) -> tuple[bool, str | None]:
    """Validate against VenueSearchResponseBody."""
    try:
        VenueSearchResponseBody(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def _validate_city_list(data: dict) -> tuple[bool, str | None]:
    """Validate against CityListResponseBody."""
    try:
        CityListResponseBody(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)


def _probe_calendar(client: ResyHttpClient, params: dict) -> dict:
    """Probe GET /4/venue/calendar."""
    endpoint = ResyEndpoints.CALENDAR.value
    today = date.today()
    end = today + timedelta(days=90)
    req_params = {
        "venue_id": str(params.get("venue_id", "2")),
        "num_seats": int(params.get("num_seats", 2)),
        "start_date": params.get("start_date", today.strftime("%Y-%m-%d")),
        "end_date": params.get("end_date", end.strftime("%Y-%m-%d")),
    }
    start = time.perf_counter()
    resp = client.request_no_raise("GET", endpoint, params=req_params, timeout=REQUEST_TIMEOUT)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw_json, raw_text = _try_parse_json(resp.text)
    schema_valid, schema_errors = _validate_calendar(raw_json) if raw_json else (None, "No JSON")
    return {
        "endpoint": endpoint,
        "method": "GET",
        "request_params": req_params,
        "status_code": resp.status_code,
        "time_ms": elapsed_ms,
        "rate_limit_headers": _extract_rate_limit_headers(resp),
        "raw_response": raw_json if raw_json is not None else raw_text,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
    }


def _probe_find(client: ResyHttpClient, params: dict) -> dict:
    """Probe POST /4/find."""
    endpoint = ResyEndpoints.FIND.value
    day = params.get("day") or date.today().strftime("%Y-%m-%d")
    body = {
        "lat": 0,
        "long": 0,
        "day": day,
        "party_size": int(params.get("party_size", 2)),
        "venue_id": int(params["venue_id"]) if params.get("venue_id") else None,
    }
    if body["venue_id"] is None:
        body["venue_id"] = 2
    start = time.perf_counter()
    resp = client.request_no_raise("POST", endpoint, json=body, timeout=REQUEST_TIMEOUT)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw_json, raw_text = _try_parse_json(resp.text)
    schema_valid, schema_errors = _validate_find(raw_json) if raw_json else (None, "No JSON")
    return {
        "endpoint": endpoint,
        "method": "POST",
        "request_params": body,
        "status_code": resp.status_code,
        "time_ms": elapsed_ms,
        "rate_limit_headers": _extract_rate_limit_headers(resp),
        "raw_response": raw_json if raw_json is not None else raw_text,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
    }


def _probe_venue(client: ResyHttpClient, params: dict) -> dict:
    """Probe GET /3/venue."""
    endpoint = ResyEndpoints.VENUE.value
    venue_id = str(params.get("venue_id", "2"))
    req_params = {"id": venue_id}
    start = time.perf_counter()
    resp = client.request_no_raise("GET", endpoint, params=req_params, timeout=(5, 30))
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw_json, raw_text = _try_parse_json(resp.text)
    schema_valid, schema_errors = _validate_venue(raw_json) if raw_json else (None, "No JSON")
    return {
        "endpoint": endpoint,
        "method": "GET",
        "request_params": req_params,
        "status_code": resp.status_code,
        "time_ms": elapsed_ms,
        "rate_limit_headers": _extract_rate_limit_headers(resp),
        "raw_response": raw_json if raw_json is not None else raw_text,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
    }


def _probe_search(client: ResyHttpClient, params: dict) -> dict:
    """Probe POST /3/venuesearch/search."""
    endpoint = ResyEndpoints.VENUE_SEARCH.value
    query = params.get("query", "pizza")
    body = VenueSearchRequestBody(query=query).model_dump(exclude_none=True)
    start = time.perf_counter()
    resp = client.request_no_raise("POST", endpoint, json=body, timeout=(5, 30))
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw_json, raw_text = _try_parse_json(resp.text)
    schema_valid, schema_errors = _validate_venue_search(raw_json) if raw_json else (None, "No JSON")
    return {
        "endpoint": endpoint,
        "method": "POST",
        "request_params": body,
        "status_code": resp.status_code,
        "time_ms": elapsed_ms,
        "rate_limit_headers": _extract_rate_limit_headers(resp),
        "raw_response": raw_json if raw_json is not None else raw_text,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
    }


def _probe_city_list(client: ResyHttpClient, params: dict) -> dict:
    """Probe GET /3/cities/{slug}/list/{list_type}."""
    slug = params.get("slug", "new-york-ny")
    list_type = params.get("list_type", "climbing")
    limit = int(params.get("limit", 10))
    path = ResyEndpoints.CITY_LIST.value.replace("{slug}", slug).replace("{list_type}", list_type)
    endpoint = path
    req_params = {"limit": limit}
    start = time.perf_counter()
    resp = client.request_no_raise("GET", endpoint, params=req_params, timeout=REQUEST_TIMEOUT)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw_json, raw_text = _try_parse_json(resp.text)
    schema_valid, schema_errors = _validate_city_list(raw_json) if raw_json else (None, "No JSON")
    return {
        "endpoint": endpoint,
        "method": "GET",
        "request_params": {"slug": slug, "list_type": list_type, "limit": limit},
        "status_code": resp.status_code,
        "time_ms": elapsed_ms,
        "rate_limit_headers": _extract_rate_limit_headers(resp),
        "raw_response": raw_json if raw_json is not None else raw_text,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
    }


PROBES = {
    "calendar": _probe_calendar,
    "find": _probe_find,
    "venue": _probe_venue,
    "search": _probe_search,
    "city_list": _probe_city_list,
}


@on_request(
    cors=CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]),
    timeout_sec=120,
    memory=MemoryOption.GB_1,
)
@with_sentry_trace
def resy_debug(req: Request):
    """
    POST /resy_debug
    Body: { "endpoint": "calendar" | "find" | "venue" | "search" | "city_list" | "all", "params": {...} }
    Probes Resy API and returns diagnostic payload (auth, results, schema validation).
    Always returns 200; errors are included in the payload.
    """
    payload = {"success": False, "auth": None, "results": [], "error": None}
    try:
        body = req.get_json(silent=True) or {}
        endpoint_name = (body.get("endpoint") or "").strip().lower()
        params = body.get("params") or {}

        if not endpoint_name:
            payload["error"] = "Missing 'endpoint' in body (calendar, find, venue, search, city_list, all)"
            return payload, 200

        # Auth
        try:
            http_client, token_preview, auth_time_ms = _auth_and_build_client()
            payload["auth"] = {
                "status": "ok",
                "token_preview": token_preview,
                "time_ms": auth_time_ms,
            }
        except Exception as e:
            logger.warning("Debug auth failed: %s", e)
            payload["auth"] = {
                "status": "error",
                "message": str(e),
                "time_ms": None,
            }
            payload["error"] = "Auth failed: " + str(e)
            return payload, 200

        # Probe one or all
        if endpoint_name == "all":
            for name, probe_fn in PROBES.items():
                try:
                    result = probe_fn(http_client, params)
                    payload["results"].append(result)
                except Exception as e:
                    logger.warning("Probe %s failed: %s", name, e)
                    payload["results"].append({
                        "endpoint": name,
                        "error": str(e),
                        "status_code": None,
                        "time_ms": None,
                        "schema_valid": None,
                        "schema_errors": None,
                    })
        else:
            if endpoint_name not in PROBES:
                payload["error"] = (
                    "Unknown endpoint: %s (use calendar, find, venue, search, city_list, all)"
                    % endpoint_name
                )
                return payload, 200
            result = PROBES[endpoint_name](http_client, params)
            payload["results"].append(result)

        payload["success"] = True
        return payload, 200

    except Exception as e:
        logger.exception("resy_debug failed: %s", e)
        payload["error"] = str(e)
        return payload, 200
