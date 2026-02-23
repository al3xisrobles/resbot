"""Shared constants for the API layer."""

# Gemini model used for AI features (summarization, search grounding)
GEMINI_MODEL = "gemini-2.5-pro"

# Drop time discovery: polling window and intervals (adaptive strategy)
DISCOVERY_WINDOW_BEFORE_MINUTES = 30
DISCOVERY_WINDOW_AFTER_MINUTES = 30
DISCOVERY_POLL_EARLY_SECONDS = 60   # >10 min before expected drop
DISCOVERY_POLL_ACTIVE_SECONDS = 15  # -10 to +5 min around drop
DISCOVERY_POLL_LATE_SECONDS = 30    # +5 to +30 min after drop
DISCOVERY_OBSERVATIONS_CAP = 10    # max observations stored per venue
DISCOVERY_RATE_LIMIT_BACKOFF_MULTIPLIER = 2  # double interval on 429
