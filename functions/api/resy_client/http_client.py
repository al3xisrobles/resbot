"""
Centralized HTTP transport for all Resy API calls.
Single point for request execution, error normalization, and logging.
"""

import logging
import time
from typing import Any

import sentry_sdk
import requests
from requests import Session

from .constants import RESY_BASE_URL, ResyEndpoints
from .errors import (
    RateLimitError,
    ResyApiError,
    ResyAuthError,
    ResyInvalidCredentialsError,
    ResySessionExpiredError,
    ResyTransientError,
)
from .models import ResyConfig

logger = logging.getLogger(__name__)

# Timeout (connect, read) in seconds
REQUEST_TIMEOUT = (5, 10)

# Redact keys that may appear in logged params/body
REDACT_KEYS = frozenset({"password", "email", "token", "book_token", "struct_payment_method"})

# Max chars of response body to log on error
ERROR_BODY_TRUNCATE = 500

# HTTP statuses from Resy that are transient and safe to retry.
TRANSIENT_STATUS = frozenset({500, 502, 503, 504})

# Retry policy for transient upstream failures (transient statuses, rate limits, and
# connection errors). Reads are idempotent, so retrying is safe; the only mutating
# endpoint -- booking -- is excluded so a retry can never create a duplicate reservation.
MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.3  # seconds; exponential backoff: 0.3, 0.6, ...
NON_RETRYABLE_ENDPOINTS = frozenset({ResyEndpoints.BOOK.value})


def _build_session(config: ResyConfig) -> Session:
    """Build a requests.Session with Resy headers. Token may be empty for auth-only."""
    session = Session()
    token = config.token or ""
    headers = {
        "Authorization": config.get_authorization(),
        "X-Resy-Auth-Token": token,
        "X-Resy-Universal-Auth": token,
        "Origin": "https://resy.com",
        "X-origin": "https://resy.com",
        "Referer": "https://resy.com/",
        "Referrer": "https://resy.com/",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    session.headers.update(headers)
    return session


def _redact_for_log(obj: dict | None) -> dict | None:
    """Return a copy of obj with sensitive values redacted for logging."""
    if obj is None:
        return None
    out = {}
    for k, v in obj.items():
        key_lower = k.lower() if isinstance(k, str) else ""
        if key_lower in REDACT_KEYS or any(r in key_lower for r in ("token", "password")):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _redact_for_log(v)
        else:
            out[k] = v
    return out


def _truncate(text: str | None, max_len: int = ERROR_BODY_TRUNCATE) -> str:
    """Truncate string for error logging."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


class ResyHttpClient:
    """
    Single HTTP transport for Resy API. All calls go through _request.
    Does not perform retries or Pydantic parsing; callers do that.
    """

    def __init__(self, session: Session, max_retry_delay: float | None = None,
                 max_attempts: int = MAX_RETRY_ATTEMPTS):
        self.session = session
        # Attempts per request, including the first. Snipes keep the default; the watch
        # poller uses 1, because retrying into a bot block only extends the block.
        self.max_attempts = max_attempts
        # Longest wait a retry may take. None means no cap (snipes wait out Retry-After);
        # the watch poller sets one so a long Retry-After fails fast and backs the target off
        # instead of sleeping past the tick's timeout.
        self.max_retry_delay = max_retry_delay

    @classmethod
    def build(cls, config: ResyConfig) -> "ResyHttpClient":
        session = _build_session(config)
        return cls(session)

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """GET request. Raises ResyApiError subclasses on non-2xx."""
        return self._request("GET", endpoint, params=params, timeout=timeout)

    def post_json(
        self,
        endpoint: str,
        body: dict[str, Any] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """POST with JSON body. Raises ResyApiError subclasses on non-2xx."""
        return self._request("POST", endpoint, json=body, timeout=timeout)

    def post_form(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """POST with form-encoded body. Raises ResyApiError subclasses on non-2xx."""
        return self._request(
            "POST",
            endpoint,
            data=data,
            extra_headers=extra_headers,
            timeout=timeout,
        )

    def request_no_raise(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """
        Make request and return response without raising on non-2xx.
        For use by debug/tooling that needs to inspect status, headers, and body.
        """
        url = RESY_BASE_URL + endpoint
        log_params = _redact_for_log(params)
        log_body = _redact_for_log(json if json is not None else data)

        with sentry_sdk.start_span(
            op="http.client",
            name=f"resy {method} {endpoint}",
            description=f"{method} {endpoint}",
        ) as span:
            span.set_tag("http.url", url)
            span.set_tag("http.method", method)
            span.set_tag("resy.endpoint", endpoint)

            headers = dict(extra_headers) if extra_headers else {}
            if json is not None:
                headers.setdefault("Content-Type", "application/json")
            if data is not None and "Content-Type" not in headers:
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

            logger.info(
                "Resy request %s %s params=%s body=%s",
                method,
                endpoint,
                log_params,
                log_body,
            )

            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers if headers else None,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                logger.error("Resy request failed %s %s: %s", method, endpoint, e)
                span.set_status("internal_error")
                raise

            span.set_tag("http.status_code", resp.status_code)
            resp_body_preview = resp.text
            if not resp.ok and resp_body_preview:
                resp_body_preview = _truncate(resp_body_preview)
            logger.info(
                "Resy response %s %s status=%s body=%s",
                method,
                endpoint,
                resp.status_code,
                resp_body_preview if not resp.ok else "(success)",
            )
            span.set_status("ok" if resp.ok else "internal_error")
            return resp

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        """Execute a request, retrying transient upstream failures with backoff.

        Retries on transient Resy statuses (500/502/503/504), rate limits (429, honoring
        Retry-After), and connection errors -- the failures that make Resy flaky. Auth
        errors, schema mismatches, and read timeouts are not retried, and booking is never
        retried so we never risk a duplicate reservation.
        """
        retryable = endpoint not in NON_RETRYABLE_ENDPOINTS
        attempt = 0
        while True:
            try:
                return self._send_once(
                    method,
                    endpoint,
                    params=params,
                    json=json,
                    data=data,
                    extra_headers=extra_headers,
                    timeout=timeout,
                )
            except (ResyTransientError, RateLimitError, requests.exceptions.ConnectionError) as exc:
                attempt += 1
                if not retryable or attempt >= self.max_attempts:
                    raise
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                    delay = max(delay, exc.retry_after)
                if self.max_retry_delay is not None and delay > self.max_retry_delay:
                    raise
                logger.warning(
                    "Retrying Resy %s %s after transient failure (attempt %s/%s, waiting %.2fs): %s",
                    method,
                    endpoint,
                    attempt,
                    self.max_attempts,
                    delay,
                    exc,
                )
                time.sleep(delay)

    def _send_once(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: tuple[int, int] = REQUEST_TIMEOUT,
    ) -> requests.Response:
        url = RESY_BASE_URL + endpoint
        log_params = _redact_for_log(params)
        log_body = _redact_for_log(json if json is not None else data)

        with sentry_sdk.start_span(
            op="http.client",
            name=f"resy {method} {endpoint}",
            description=f"{method} {endpoint}",
        ) as span:
            span.set_tag("http.url", url)
            span.set_tag("http.method", method)
            span.set_tag("resy.endpoint", endpoint)

            headers = dict(extra_headers) if extra_headers else {}
            if json is not None:
                headers.setdefault("Content-Type", "application/json")
            if data is not None and "Content-Type" not in headers:
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

            logger.info(
                "Resy request %s %s params=%s body=%s",
                method,
                endpoint,
                log_params,
                log_body,
            )

            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers if headers else None,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                logger.error("Resy request failed %s %s: %s", method, endpoint, e)
                span.set_status("internal_error")
                raise

            span.set_tag("http.status_code", resp.status_code)

            # Log response (truncate body on error)
            resp_body_preview = resp.text
            if not resp.ok and resp_body_preview:
                resp_body_preview = _truncate(resp_body_preview)
            logger.info(
                "Resy response %s %s status=%s body=%s",
                method,
                endpoint,
                resp.status_code,
                resp_body_preview if not resp.ok else "(success)",
            )

            if resp.ok:
                span.set_status("ok")
                return resp

            # Normalize errors with status_code, response_body, endpoint
            status = resp.status_code
            body = resp.text or ""
            body_truncated = _truncate(body)

            if status == 429:
                retry_after_header = resp.headers.get("Retry-After")
                retry_after = float(retry_after_header) if retry_after_header else None
                logger.warning(
                    "Resy rate limit (429) %s Retry-After=%s",
                    endpoint,
                    retry_after_header,
                )
                span.set_status("resource_exhausted")
                raise RateLimitError(
                    f"Rate limit exceeded: {body_truncated}",
                    status_code=429,
                    response_body=body,
                    endpoint=endpoint,
                    retry_after=retry_after,
                )

            if status in (401, 403):
                logger.warning("Resy auth error %s %s: %s", status, endpoint, body_truncated)
                span.set_status("unauthenticated" if status == 401 else "permission_denied")
                raise ResyAuthError(
                    f"Auth error {status}: {body_truncated}",
                    status_code=status,
                    response_body=body,
                    endpoint=endpoint,
                )

            if status == 419:
                # Resy returns the same 419 "Unauthorized" body for two different
                # situations, distinguishable only by endpoint:
                #   - on /4/auth/password it means the login credentials are wrong
                #   - on every other (authenticated) endpoint it means the session
                #     token is expired or rejected
                span.set_status("unauthenticated")
                if endpoint == ResyEndpoints.PASSWORD_AUTH.value:
                    logger.info("Resy invalid credentials (419) %s: %s", endpoint, body_truncated)
                    raise ResyInvalidCredentialsError(
                        f"Invalid username or password: {body_truncated}",
                        status_code=419,
                        response_body=body,
                        endpoint=endpoint,
                    )
                logger.info("Resy session expired (419) %s: %s", endpoint, body_truncated)
                raise ResySessionExpiredError(
                    f"Resy session expired: {body_truncated}",
                    status_code=419,
                    response_body=body,
                    endpoint=endpoint,
                )

            if status in TRANSIENT_STATUS:
                logger.warning(
                    "Resy transient error %s %s: %s",
                    status,
                    endpoint,
                    body_truncated,
                )
                span.set_status("internal_error")
                raise ResyTransientError(
                    f"Transient error {status}: {body_truncated}",
                    status_code=status,
                    response_body=body,
                    endpoint=endpoint,
                )

            span.set_status("internal_error")
            raise ResyApiError(
                f"Resy API error {status}: {body_truncated}",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
