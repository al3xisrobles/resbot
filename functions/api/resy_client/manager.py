from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import logging
from requests import HTTPError
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError
from .errors import (
    NoSlotsError,
    ExhaustedRetriesError,
    SlotTakenError,
    RateLimitError,
    ResyTransientError,
    ResyAuthError,
)
from .constants import (
    N_RETRIES,
    SECONDS_TO_WAIT_BETWEEN_RETRIES,
)
from .models import (
    ResyConfig,
    ReservationRequest,
    TimedReservationRequest,
    ReservationRetriesConfig,
)
from .model_builders import (
    build_find_request_body,
    build_get_slot_details_body,
    build_book_request_body,
)
from .api_access import ResyApiAccess
from .selectors import AbstractSelector, SimpleSelector

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

# Rate limit backoff configuration
RATE_LIMIT_BASE_WAIT = .05  # Start with 50ms wait
RATE_LIMIT_MAX_WAIT = 4.0   # Cap at 4 seconds (to not waste snipe window)
RATE_LIMIT_MULTIPLIER = 2.0  # Double wait time each consecutive rate limit


class ResyManager:
    @classmethod
    def build(cls, config: ResyConfig) -> "ResyManager":
        api_access = ResyApiAccess.build(config)
        selector = SimpleSelector()
        retry_config = ReservationRetriesConfig(
            seconds_between_retries=SECONDS_TO_WAIT_BETWEEN_RETRIES,
            n_retries=N_RETRIES,
        )
        return cls(config, api_access, selector, retry_config)

    def __init__(
        self,
        config: ResyConfig,
        api_access: ResyApiAccess,
        slot_selector: AbstractSelector,
        retry_config: ReservationRetriesConfig,
    ):
        self.config = config
        self.api_access = api_access
        self.selector = slot_selector
        self.retry_config = retry_config

    def get_venue_id(self, address: str):  # noqa: ARG002
        """
        TODO: get venue id from string address
            will use geolocator to get lat/long
        :return:
        """
        raise NotImplementedError("get_venue_id is not yet implemented")

    def make_reservation(self, reservation_request: ReservationRequest) -> str:
        body = build_find_request_body(reservation_request)

        slots = self.api_access.find_booking_slots(body)

        if len(slots) == 0:
            logger.info("No slots found... Returned: %s", slots)
            raise NoSlotsError("No Slots Found")

        logger.info("Found %s slots", len(slots))
        logger.info(slots)

        selected_slot = self.selector.select(slots, reservation_request)

        logger.info(selected_slot)
        details_request = build_get_slot_details_body(
            reservation_request, selected_slot
        )
        logger.info(details_request)
        logger.info("Getting booking token for slot %s", selected_slot.date.start)
        token = self.api_access.get_booking_token(details_request)
        logger.info("Got booking token: %s", token)

        booking_request = build_book_request_body(token, self.config)

        try:
            logger.info("Attempting to book slot...")
            resy_token = self.api_access.book_slot(booking_request)
            return resy_token
        except ResyAuthError as e:
            logger.error("Auth error - token may be expired: %s", e)
            raise
        except HTTPError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", "N/A")
            logger.error(
                "Booking failed - Error type: %s, Status: %s, Message: %s",
                type(e).__name__,
                status_code,
                str(e),
            )
            raise SlotTakenError("Failed to book slot: %s" % str(e)) from e
        except Exception as e:
            if hasattr(e, "status_code"):
                logger.error(
                    "Booking failed - %s %s: %s",
                    getattr(e, "status_code", ""),
                    getattr(e, "endpoint", ""),
                    getattr(e, "response_body", "")[:200] or str(e),
                )
            raise SlotTakenError("Failed to book slot: %s" % str(e)) from e

    def _try_book_slot(self, slot, reservation_request: ReservationRequest) -> str:
        """
        Attempt to book a single slot. Used by parallel booking.
        Returns resy_token on success, raises on failure.
        """
        details_request = build_get_slot_details_body(reservation_request, slot)
        token = self.api_access.get_booking_token(details_request)
        booking_request = build_book_request_body(token, self.config)
        return self.api_access.book_slot(booking_request)

    def make_reservation_parallel(self, reservation_request: ReservationRequest, n_slots: int = 3) -> str:
        """
        Find slots, then attempt to book top N candidates in parallel.
        First successful booking wins; others are abandoned.
        """
        body = build_find_request_body(reservation_request)
        slots = self.api_access.find_booking_slots(body)

        if len(slots) == 0:
            logger.info("No slots found... Returned: %s", slots)
            raise NoSlotsError("No Slots Found")

        logger.info("Found %s slots", len(slots))

        # Get top N candidates
        top_slots = self.selector.select_top_n(slots, reservation_request, n=n_slots)
        logger.info("Selected top %s slots for parallel booking: %s", len(top_slots), [s.date.start for s in top_slots])

        errors = []

        # Use ThreadPoolExecutor to book in parallel
        with ThreadPoolExecutor(max_workers=n_slots) as executor:
            future_to_slot = {
                executor.submit(self._try_book_slot, slot, reservation_request): slot
                for slot in top_slots
            }

            for future in as_completed(future_to_slot):
                slot = future_to_slot[future]
                try:
                    resy_token = future.result()
                    logger.info("Successfully booked slot at %s!", slot.date.start)
                    # Cancel remaining futures (best effort - they may already be running)
                    for f in future_to_slot:
                        f.cancel()
                    return resy_token
                except Exception as e:  # pylint: disable=broad-exception-caught
                    # Intentionally catching all exceptions from parallel futures
                    logger.warning("Failed to book slot at %s: %s", slot.date.start, e)
                    errors.append(e)

        # All attempts failed
        raise SlotTakenError(f"All {len(top_slots)} parallel booking attempts failed: {errors}")

    def make_reservation_with_retries(
        self, reservation_request: ReservationRequest
    ) -> str:
        rate_limit_wait = RATE_LIMIT_BASE_WAIT

        for attempt in range(self.retry_config.n_retries):
            try:
                result = self.make_reservation(reservation_request)
                return result

            except NoSlotsError as e:
                logger.info(
                    "no slots (%s), retrying; currently %s",
                    str(e),
                    datetime.now().isoformat(),
                )

            except SlotTakenError:
                if not self.config.retry_on_taken_slot:
                    raise
                logger.info(
                    "slot taken (attempt %s/%s), retrying; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    datetime.now().isoformat(),
                )

            except ResyTransientError as transient_err:
                logger.warning(
                    "Transient Resy error (attempt %s/%s): %s %s - %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    transient_err.status_code,
                    transient_err.endpoint,
                    (transient_err.response_body[:200] if transient_err.response_body else "no body"),
                )

            except ResyAuthError as auth_err:
                logger.error("Auth error - token may be expired: %s", auth_err)
                raise

            except RateLimitError as rate_err:
                wait_time = rate_err.retry_after if rate_err.retry_after else rate_limit_wait
                wait_time = min(wait_time, RATE_LIMIT_MAX_WAIT)
                logger.warning(
                    "Rate limited (attempt %s/%s), waiting %s s before retry; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    wait_time,
                    datetime.now().isoformat(),
                )
                time.sleep(wait_time)
                rate_limit_wait = min(rate_limit_wait * RATE_LIMIT_MULTIPLIER, RATE_LIMIT_MAX_WAIT)
                continue

            except (Timeout, RequestsConnectionError) as net_err:
                logger.warning(
                    "Network error (attempt %s/%s): %s - %s, retrying; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    type(net_err).__name__,
                    str(net_err),
                    datetime.now().isoformat(),
                )

        raise ExhaustedRetriesError(
            "Retried %s times, without finding a slot" % self.retry_config.n_retries
        )

    def make_reservation_parallel_with_retries(
        self, reservation_request: ReservationRequest, n_slots: int = 3
    ) -> str:
        """
        Like make_reservation_with_retries but uses parallel booking for each attempt.
        """
        rate_limit_wait = RATE_LIMIT_BASE_WAIT

        for attempt in range(self.retry_config.n_retries):
            try:
                return self.make_reservation_parallel(reservation_request, n_slots=n_slots)

            except NoSlotsError as e:
                logger.info(
                    "no slots (%s), retrying; currently %s",
                    str(e),
                    datetime.now().isoformat(),
                )

            except SlotTakenError:
                if not self.config.retry_on_taken_slot:
                    raise
                logger.info(
                    "all parallel slots taken (attempt %s/%s), retrying; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    datetime.now().isoformat(),
                )

            except ResyTransientError as transient_err:
                logger.warning(
                    "Transient Resy error (attempt %s/%s): %s %s - %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    transient_err.status_code,
                    transient_err.endpoint,
                    (transient_err.response_body[:200] if transient_err.response_body else "no body"),
                )

            except ResyAuthError as auth_err:
                logger.error("Auth error - token may be expired: %s", auth_err)
                raise

            except RateLimitError as rate_err:
                # Use retry_after from API if available, otherwise use exponential backoff
                wait_time = rate_err.retry_after if rate_err.retry_after else rate_limit_wait
                wait_time = min(wait_time, RATE_LIMIT_MAX_WAIT)
                logger.warning(
                    "Rate limited (attempt %s/%s), waiting %s s before retry; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    wait_time,
                    datetime.now().isoformat(),
                )
                time.sleep(wait_time)
                rate_limit_wait = min(rate_limit_wait * RATE_LIMIT_MULTIPLIER, RATE_LIMIT_MAX_WAIT)
                continue

            except (Timeout, RequestsConnectionError) as net_err:
                logger.warning(
                    "Network error (attempt %s/%s): %s - %s, retrying; currently %s",
                    attempt + 1,
                    self.retry_config.n_retries,
                    type(net_err).__name__,
                    str(net_err),
                    datetime.now().isoformat(),
                )

        raise ExhaustedRetriesError(
            "Retried %s times with parallel booking, without securing a slot"
            % self.retry_config.n_retries
        )

    def _get_drop_time(self, reservation_request: TimedReservationRequest) -> datetime:
        now = datetime.now()
        return datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=reservation_request.expected_drop_hour,
            minute=reservation_request.expected_drop_minute,
        )

    def make_reservation_at_opening_time(
        self, reservation_request: TimedReservationRequest
    ) -> str:
        """
        cycle until we hit the opening time, then run & return the reservation
        """
        drop_time = self._get_drop_time(reservation_request)
        last_check = datetime.now()
        logger.info("waiting until drop time at %s", drop_time)

        while True:
            if datetime.now() < drop_time:
                if datetime.now() - last_check > timedelta(seconds=10):
                    logger.info("%s: still waiting", datetime.now())
                    last_check = datetime.now()
                continue

            logger.info("time reached, making a reservation now! %s", datetime.now())
            return self.make_reservation_with_retries(
                reservation_request.reservation_request
            )
