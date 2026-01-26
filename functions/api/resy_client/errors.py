class NoSlotsError(Exception):
    """Raised when no slots are available for the requested time/date."""


class ExhaustedRetriesError(Exception):
    """Raised when all retry attempts have been exhausted."""


class SlotTakenError(Exception):
    """Raised when a slot booking fails because it was already taken."""


class RateLimitError(Exception):
    """Raised when Resy API returns 429 Too Many Requests."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after  # Suggested wait time in seconds
