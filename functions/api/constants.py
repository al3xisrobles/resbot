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

# Cancellation watch: one shared poller for all watches (see specs/cancellation-watch/SPEC.md)
WATCH_TICK_SECOND = 50              # second of each minute the tick is dispatched
WATCH_TICK_TIMEOUT_SECONDS = 55     # bounds the worst-case bill; see Cost in the spec
WATCH_QUIET_TIMEZONE = "America/New_York"
WATCH_QUIET_START_HOUR = 2          # no ticks from 2am...
WATCH_QUIET_END_HOUR = 7            # ...until 7am
WATCH_MAX_TARGETS = 25              # active (venueId, partySize) pairs across all users
WATCH_MAX_PER_USER = 5              # active watches per user
WATCH_POLL_WORKERS = 8              # targets polled in parallel per tick
WATCH_TARGET_BACKOFF_SECONDS = 300  # skip a target this long after a 429
WATCH_RELEASE_WINDOW_MINUTES = 5    # openings this close to a venue's drop time count as a release
WATCH_MAX_BOOKING_FAILURES = 3      # non-transient failures before a watch ends
WATCH_CLAIM_STALE_SECONDS = 120     # a claim older than this is treated as abandoned
WATCH_BOOKING_ENABLED_ENV = "WATCH_BOOKING_ENABLED"  # "true" turns booking on; default is shadow mode
