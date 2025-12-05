class NoSlotsError(Exception):
    pass


class ExhaustedRetriesError(Exception):
    pass


class SlotTakenError(Exception):
    """Raised when a slot booking fails because it was already taken"""
    pass
