class NoSlotsError(Exception):
    """Raised when no slots are available for the requested time/date."""


class ExhaustedRetriesError(Exception):
    """Raised when all retry attempts have been exhausted."""


class SlotTakenError(Exception):
    """Raised when a slot booking fails because it was already taken."""
