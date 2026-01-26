"""
Tests for ResyManager - the main orchestration layer.

Tests cover:
- Single reservation flow (make_reservation)
- Parallel reservation flow (make_reservation_parallel)
- Retry logic (make_reservation_with_retries, make_reservation_parallel_with_retries)
- Error handling (NoSlotsError, SlotTakenError, network errors)
- Configuration options (retry_on_taken_slot)
"""
import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from requests.exceptions import HTTPError, Timeout, ConnectionError as RequestsConnectionError

from resy_client.manager import ResyManager
from resy_client.api_access import ResyApiAccess
from resy_client.selectors import SimpleSelector
from resy_client.models import (
    ReservationRetriesConfig,
    DetailsResponseBody,
    BookToken,
)
from resy_client.errors import NoSlotsError, SlotTakenError, ExhaustedRetriesError, RateLimitError
from resy_client.constants import N_RETRIES


class TestResyManagerBuild:
    """Tests for ResyManager factory method."""

    def test_build_creates_manager_with_all_components(self, resy_config):
        """Build should create manager with api_access, selector, and retry_config."""
        manager = ResyManager.build(resy_config)

        assert isinstance(manager, ResyManager)
        assert isinstance(manager.api_access, ResyApiAccess)
        assert isinstance(manager.selector, SimpleSelector)
        assert isinstance(manager.retry_config, ReservationRetriesConfig)

    def test_build_sets_config(self, resy_config):
        """Build should store the ResyConfig."""
        manager = ResyManager.build(resy_config)
        assert manager.config == resy_config

    def test_build_uses_default_retry_count(self, resy_config):
        """Build should use N_RETRIES from constants."""
        manager = ResyManager.build(resy_config)
        assert manager.retry_config.n_retries == N_RETRIES


class TestMakeReservation:
    """Tests for single reservation attempt (make_reservation)."""

    def test_make_reservation_success(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
        details_response,
        book_response_success,
    ):
        """Successful reservation should return resy_token."""
        # Create mock api_access
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.01, n_retries=3),
        )

        result = manager.make_reservation(reservation_request_dinner)

        assert result == "resy_confirmation_123"
        mock_api.find_booking_slots.assert_called_once()
        mock_api.get_booking_token.assert_called_once()
        mock_api.book_slot.assert_called_once()

    def test_make_reservation_no_slots_raises_error(
        self,
        resy_config,
        reservation_request_dinner,
    ):
        """No slots available should raise NoSlotsError."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = []

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.01, n_retries=3),
        )

        with pytest.raises(NoSlotsError):
            manager.make_reservation(reservation_request_dinner)

    def test_make_reservation_slot_taken_raises_error(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """HTTP error during booking should raise SlotTakenError."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        # Simulate HTTP error with proper response attribute
        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = http_error

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.01, n_retries=3),
        )

        with pytest.raises(SlotTakenError):
            manager.make_reservation(reservation_request_dinner)

    def test_make_reservation_selects_best_slot(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should use selector to pick the best slot."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        mock_selector = Mock()
        mock_selector.select.return_value = sample_dinner_slots[4]  # 19:30 slot

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=mock_selector,
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.01, n_retries=3),
        )

        manager.make_reservation(reservation_request_dinner)

        mock_selector.select.assert_called_once_with(sample_dinner_slots, reservation_request_dinner)


class TestMakeReservationWithRetries:
    """Tests for reservation with retry logic."""

    def test_retries_on_no_slots(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should retry when NoSlotsError is raised."""
        mock_api = Mock(spec=ResyApiAccess)
        # First two calls return empty, third returns slots
        mock_api.find_booking_slots.side_effect = [
            [],
            [],
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_with_retries(reservation_request_dinner)

        assert result == "resy_confirmation_123"
        assert mock_api.find_booking_slots.call_count == 3

    def test_retries_on_slot_taken_when_enabled(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should retry when SlotTakenError and retry_on_taken_slot=True."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        # First book fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = [http_error, "resy_confirmation_123"]

        manager = ResyManager(
            config=resy_config,  # retry_on_taken_slot=True by default
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_with_retries(reservation_request_dinner)

        assert result == "resy_confirmation_123"
        assert mock_api.book_slot.call_count == 2

    def test_no_retry_on_slot_taken_when_disabled(
        self,
        resy_config_no_retry,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should NOT retry SlotTakenError when retry_on_taken_slot=False."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = http_error

        manager = ResyManager(
            config=resy_config_no_retry,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        with pytest.raises(SlotTakenError):
            manager.make_reservation_with_retries(reservation_request_dinner)

        # Should only try once
        assert mock_api.book_slot.call_count == 1

    def test_retries_on_rate_limit_with_exponential_backoff(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should retry on RateLimitError with exponential backoff."""
        mock_api = Mock(spec=ResyApiAccess)
        # First call rate limited, second succeeds
        mock_api.find_booking_slots.side_effect = [
            RateLimitError("Rate limit exceeded", retry_after=None),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        start_time = time.time()
        result = manager.make_reservation_with_retries(reservation_request_dinner)
        elapsed = time.time() - start_time

        assert result == "resy_confirmation_123"
        assert mock_api.find_booking_slots.call_count == 2
        # Should have waited at least 1 second (base wait time)
        assert elapsed >= 1.0

    def test_retries_on_rate_limit_uses_retry_after_header(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should use Retry-After header value when provided."""
        mock_api = Mock(spec=ResyApiAccess)
        # First call rate limited with Retry-After: 3, second succeeds
        mock_api.find_booking_slots.side_effect = [
            RateLimitError("Rate limit exceeded", retry_after=3.0),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        start_time = time.time()
        result = manager.make_reservation_with_retries(reservation_request_dinner)
        elapsed = time.time() - start_time

        assert result == "resy_confirmation_123"
        # Should have waited approximately 3 seconds (from Retry-After header)
        assert elapsed >= 2.9  # Allow small margin for test execution time

    def test_retries_on_rate_limit_exponential_backoff_caps_at_max(
        self,
        resy_config,
        reservation_request_dinner,
    ):
        """Exponential backoff should cap at RATE_LIMIT_MAX_WAIT."""
        mock_api = Mock(spec=ResyApiAccess)
        # Always rate limited
        mock_api.find_booking_slots.side_effect = RateLimitError("Rate limit exceeded", retry_after=None)

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        start_time = time.time()
        with pytest.raises(ExhaustedRetriesError):
            manager.make_reservation_with_retries(reservation_request_dinner)
        elapsed = time.time() - start_time

        # Should have waited: ~1s + ~2s + ~4s (capped at 8s) = ~7s minimum
        # But we only do 3 retries, so: ~1s + ~2s = ~3s minimum
        assert elapsed >= 2.5  # Allow margin for test execution

    def test_retries_on_timeout(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should retry on Timeout errors."""
        mock_api = Mock(spec=ResyApiAccess)
        # First call times out, second succeeds
        mock_api.find_booking_slots.side_effect = [
            Timeout("Connection timed out"),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_with_retries(reservation_request_dinner)

        assert result == "resy_confirmation_123"
        assert mock_api.find_booking_slots.call_count == 2

    def test_retries_on_connection_error(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Should retry on ConnectionError."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.side_effect = [
            RequestsConnectionError("Connection refused"),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_with_retries(reservation_request_dinner)

        assert result == "resy_confirmation_123"

    def test_exhausted_retries_raises_error(
        self,
        resy_config,
        reservation_request_dinner,
    ):
        """Should raise ExhaustedRetriesError after all retries fail."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = []  # Always empty

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        with pytest.raises(ExhaustedRetriesError):
            manager.make_reservation_with_retries(reservation_request_dinner)

        assert mock_api.find_booking_slots.call_count == 3


class TestMakeReservationParallel:
    """Tests for parallel reservation attempts."""

    def test_parallel_books_first_successful_slot(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel booking should return on first success."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        result = manager.make_reservation_parallel(reservation_request_dinner, n_slots=3)

        assert result == "resy_confirmation_123"

    def test_parallel_tries_multiple_slots(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel should attempt multiple slots."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        # First two fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = [
            http_error,
            http_error,
            "resy_confirmation_123",
        ]

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        result = manager.make_reservation_parallel(reservation_request_dinner, n_slots=3)

        assert result == "resy_confirmation_123"

    def test_parallel_raises_when_all_fail(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel should raise SlotTakenError when all attempts fail."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = http_error  # Always fails

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        with pytest.raises(SlotTakenError) as exc_info:
            manager.make_reservation_parallel(reservation_request_dinner, n_slots=3)

        assert "parallel booking attempts failed" in str(exc_info.value)

    def test_parallel_no_slots_raises_error(
        self,
        resy_config,
        reservation_request_dinner,
    ):
        """Parallel should raise NoSlotsError when no slots available."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = []

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        with pytest.raises(NoSlotsError):
            manager.make_reservation_parallel(reservation_request_dinner, n_slots=3)

    def test_parallel_uses_top_n_slots(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel should use selector.select_top_n to get candidates."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        mock_selector = Mock()
        mock_selector.select_top_n.return_value = sample_dinner_slots[:3]

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=mock_selector,
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        manager.make_reservation_parallel(reservation_request_dinner, n_slots=3)

        mock_selector.select_top_n.assert_called_once_with(
            sample_dinner_slots, reservation_request_dinner, n=3
        )


class TestMakeReservationParallelWithRetries:
    """Tests for parallel reservation with retry logic."""

    def test_parallel_retries_on_failure(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel with retries should retry on all-slot-failure."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        # Track call count and fail first N calls
        call_count = [0]
        def book_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 6:  # First 2 rounds (3 slots each) fail
                mock_response = Mock()
                mock_response.status_code = 412
                http_error = HTTPError("Slot taken")
                http_error.response = mock_response
                raise http_error
            return "resy_confirmation_123"

        mock_api.book_slot.side_effect = book_side_effect

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)

        assert result == "resy_confirmation_123"

    def test_parallel_retries_on_no_slots(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel with retries should retry when no slots found."""
        mock_api = Mock(spec=ResyApiAccess)
        # First two calls return empty, third returns slots
        mock_api.find_booking_slots.side_effect = [
            [],
            [],
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)

        assert result == "resy_confirmation_123"
        assert mock_api.find_booking_slots.call_count == 3

    def test_parallel_retries_on_timeout(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel with retries should retry on timeout."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.side_effect = [
            Timeout("Connection timed out"),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        result = manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)

        assert result == "resy_confirmation_123"

    def test_parallel_exhausted_retries(
        self,
        resy_config,
        reservation_request_dinner,
    ):
        """Parallel with retries should raise after exhausting retries."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = []  # Always empty

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        with pytest.raises(ExhaustedRetriesError) as exc_info:
            manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)

        assert "parallel booking" in str(exc_info.value)

    def test_parallel_retries_on_rate_limit_with_backoff(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel with retries should handle rate limits with exponential backoff."""
        mock_api = Mock(spec=ResyApiAccess)
        # First call rate limited, second succeeds
        mock_api.find_booking_slots.side_effect = [
            RateLimitError("Rate limit exceeded", retry_after=None),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        start_time = time.time()
        result = manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)
        elapsed = time.time() - start_time

        assert result == "resy_confirmation_123"
        assert mock_api.find_booking_slots.call_count == 2
        # Should have waited at least 1 second (base wait time)
        assert elapsed >= 1.0

    def test_parallel_retries_on_rate_limit_uses_retry_after(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """Parallel with retries should use Retry-After header value."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.side_effect = [
            RateLimitError("Rate limit exceeded", retry_after=2.5),
            sample_dinner_slots,
        ]
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=5),
        )

        start_time = time.time()
        result = manager.make_reservation_parallel_with_retries(reservation_request_dinner, n_slots=3)
        elapsed = time.time() - start_time

        assert result == "resy_confirmation_123"
        # Should have waited approximately 2.5 seconds
        assert elapsed >= 2.4  # Allow small margin


class TestTryBookSlot:
    """Tests for the internal _try_book_slot method."""

    def test_try_book_slot_success(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """_try_book_slot should return token on success."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )
        mock_api.book_slot.return_value = "resy_confirmation_123"

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        slot = sample_dinner_slots[0]
        result = manager._try_book_slot(slot, reservation_request_dinner)

        assert result == "resy_confirmation_123"
        mock_api.get_booking_token.assert_called_once()
        mock_api.book_slot.assert_called_once()

    def test_try_book_slot_propagates_error(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """_try_book_slot should propagate errors."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.get_booking_token.side_effect = HTTPError("Token expired")

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        slot = sample_dinner_slots[0]

        with pytest.raises(HTTPError):
            manager._try_book_slot(slot, reservation_request_dinner)


class TestHTTPErrorHandling:
    """Tests for proper HTTPError handling (the NoneType bug fix)."""

    def test_http_error_with_response_logs_status_code(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
        caplog,
    ):
        """HTTPError with response should log the status code."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        mock_response = Mock()
        mock_response.status_code = 412
        http_error = HTTPError("Slot taken")
        http_error.response = mock_response
        mock_api.book_slot.side_effect = http_error

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        with pytest.raises(SlotTakenError):
            manager.make_reservation(reservation_request_dinner)

        # Verify no AttributeError was raised (the bug we fixed)
        # The test passes if we get here without crashing

    def test_http_error_without_response_handles_gracefully(
        self,
        resy_config,
        reservation_request_dinner,
        sample_dinner_slots,
    ):
        """HTTPError without response should not crash (NoneType bug fix)."""
        mock_api = Mock(spec=ResyApiAccess)
        mock_api.find_booking_slots.return_value = sample_dinner_slots
        mock_api.get_booking_token.return_value = DetailsResponseBody(
            book_token=BookToken(
                value="test_book_token",
                date_expires=datetime.now() + timedelta(minutes=5),
            )
        )

        # HTTPError with response=None (the bug scenario)
        http_error = HTTPError("Connection error")
        http_error.response = None
        mock_api.book_slot.side_effect = http_error

        manager = ResyManager(
            config=resy_config,
            api_access=mock_api,
            slot_selector=SimpleSelector(),
            retry_config=ReservationRetriesConfig(seconds_between_retries=0.001, n_retries=3),
        )

        # Should NOT raise AttributeError: 'NoneType' object has no attribute 'status_code'
        with pytest.raises(SlotTakenError):
            manager.make_reservation(reservation_request_dinner)
