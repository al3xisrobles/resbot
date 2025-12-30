from datetime import datetime, timedelta

import logging
from requests import HTTPError
from .errors import NoSlotsError, ExhaustedRetriesError, SlotTakenError
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

    def get_venue_id(self, address: str):
        """
        TODO: get venue id from string address
            will use geolocator to get lat/long
        :return:
        """
        pass

    def make_reservation(self, reservation_request: ReservationRequest) -> str:
        body = build_find_request_body(reservation_request)

        slots = self.api_access.find_booking_slots(body)

        if len(slots) == 0:
            logger.info(f"No slots found... Returned: {slots}")
            raise NoSlotsError("No Slots Found")
        else:
            logger.info(f"Found {len(slots)} slots")
            logger.info(slots)

        selected_slot = self.selector.select(slots, reservation_request)

        logger.info(selected_slot)
        details_request = build_get_slot_details_body(
            reservation_request, selected_slot
        )
        logger.info(details_request)
        token = self.api_access.get_booking_token(details_request)

        booking_request = build_book_request_body(token, self.config)

        try:
            logger.info("Attempting to book slot...")
            resy_token = self.api_access.book_slot(booking_request)
            return resy_token
        except HTTPError as e:
            # Log the error type and message when booking fails
            logger.error(f"Booking failed - Error type: {type(e).__name__}, Status: {e.response.status_code if hasattr(e, 'response') else 'N/A'}, Message: {str(e)}")
            # Raise SlotTakenError to allow retry logic to handle it
            raise SlotTakenError(f"Failed to book slot: {str(e)}") from e

    def make_reservation_with_retries(
        self, reservation_request: ReservationRequest
    ) -> str:
        for attempt in range(self.retry_config.n_retries):
            try:
                return self.make_reservation(reservation_request)

            except NoSlotsError as e:
                logger.info(
                    f"no slots ({str(e)}), retrying; currently {datetime.now().isoformat()}"
                )

            except SlotTakenError as e:
                if self.config.retry_on_taken_slot:
                    logger.info(
                        f"slot taken (attempt {attempt + 1}/{self.retry_config.n_retries}), retrying; currently {datetime.now().isoformat()}"
                    )
                else:
                    # If retry_on_taken_slot is False, propagate the error immediately
                    raise

        raise ExhaustedRetriesError(
            f"Retried {self.retry_config.n_retries} times, " "without finding a slot"
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
        logger.info(f"waiting until drop time at {drop_time}")

        while True:
            if datetime.now() < drop_time:
                if datetime.now() - last_check > timedelta(seconds=10):
                    logger.info(f"{datetime.now()}: still waiting")
                    last_check = datetime.now()
                continue

            logger.info(f"time reached, making a reservation now! {datetime.now()}")
            return self.make_reservation_with_retries(
                reservation_request.reservation_request
            )
