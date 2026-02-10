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
    """500/502 -- safe to retry."""


class ResyAuthError(ResyApiError):
    """401/403 -- token expired or invalid."""


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
