class ResyApiError(Exception):
    """Base error for all Resy API failures. Always carries status + body."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        endpoint: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint


class ResyTransientError(ResyApiError):
    """500/502/503/504 -- transient upstream failure, safe to retry."""


class ResyAuthError(ResyApiError):
    """401/403 -- token expired or invalid."""


class ResyInvalidCredentialsError(ResyAuthError):
    """419 on /4/auth/password -- wrong username/password at login (user error, not a bug)."""


class ResySessionExpiredError(ResyAuthError):
    """419/401 on a data endpoint -- the stored session token is expired or rejected.

    Distinct from ResyInvalidCredentialsError: the user's password is fine, but the
    long-lived Resy token has aged out (tokens last ~45 days and are not auto-refreshed,
    since we never store the password) or was otherwise rejected. Resy returns the exact
    same 419 "Unauthorized" body for both cases, so they can only be told apart by which
    endpoint produced them. Recovery is to re-authenticate (reconnect the Resy account)."""


class RateLimitError(ResyApiError):
    """429 -- rate limited, has retry_after."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response_body: str | None = None,
        endpoint: str | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message, status_code, response_body, endpoint)
        self.retry_after = retry_after


class NoSlotsError(Exception):
    """Raised when no slots are available for the requested time/date."""


class ExhaustedRetriesError(Exception):
    """Raised when all retry attempts have been exhausted."""


class SlotTakenError(Exception):
    """Raised when a slot booking fails because it was already taken."""
