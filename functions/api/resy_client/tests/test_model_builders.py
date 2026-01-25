"""
Tests for model builder functions.

Tests cover:
- build_find_request_body
- build_get_slot_details_body
- build_auth_request_body
- build_book_request_body
"""
from datetime import date, datetime, timedelta

from resy_client.model_builders import (
    build_find_request_body,
    build_get_slot_details_body,
    build_auth_request_body,
    build_book_request_body,
)
from resy_client.models import (
    ReservationRequest,
    ResyConfig,
    Slot,
    SlotConfig,
    SlotDate,
    DetailsResponseBody,
    BookToken,
)


class TestBuildFindRequestBody:
    """Tests for build_find_request_body function."""

    def test_builds_correct_structure(self):
        """Should create FindRequestBody with correct fields."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=2,
            prefer_early=True,
            ideal_date=date(2026, 2, 14),
        )

        body = build_find_request_body(request)

        assert body.venue_id == "60058"
        assert body.party_size == 2
        assert body.day == "2026-02-14"

    def test_formats_date_correctly(self):
        """Should format date as YYYY-MM-DD string."""
        request = ReservationRequest(
            venue_id="12345",
            party_size=4,
            ideal_hour=12,
            ideal_minute=0,
            window_hours=1,
            prefer_early=False,
            ideal_date=date(2026, 12, 25),
        )

        body = build_find_request_body(request)

        assert body.day == "2026-12-25"

    def test_uses_target_date_property(self):
        """Should use target_date property (works with days_in_advance)."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=2,
            prefer_early=True,
            days_in_advance=14,
        )

        body = build_find_request_body(request)

        # Should be today + 14 days
        expected_date = date.today() + timedelta(days=14)
        assert body.day == expected_date.strftime("%Y-%m-%d")

    def test_default_lat_long(self):
        """Should have default lat/long of '0'."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=2,
            prefer_early=True,
            ideal_date=date(2026, 2, 14),
        )

        body = build_find_request_body(request)

        assert body.lat == "0"
        assert body.long == "0"


class TestBuildGetSlotDetailsBody:
    """Tests for build_get_slot_details_body function."""

    def test_builds_correct_structure(self):
        """Should create DetailsRequestBody with correct fields."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=2,
            ideal_hour=19,
            ideal_minute=30,
            window_hours=2,
            prefer_early=True,
            ideal_date=date(2026, 2, 14),
        )

        slot = Slot(
            config=SlotConfig(
                id=1132070,
                type="Dining",
                token="rgs://resy/60058/4069767/2/2026-02-14/2026-02-14/19:30:00/2/Dining Room",
            ),
            date=SlotDate(
                start=datetime(2026, 2, 14, 19, 30),
                end=datetime(2026, 2, 14, 21, 15),
            ),
        )

        body = build_get_slot_details_body(request, slot)

        assert body.config_id == "rgs://resy/60058/4069767/2/2026-02-14/2026-02-14/19:30:00/2/Dining Room"
        assert body.party_size == 2
        assert body.day == "2026-02-14"

    def test_uses_slot_token_as_config_id(self):
        """Should use slot.config.token as config_id."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=4,
            ideal_hour=12,
            ideal_minute=0,
            window_hours=1,
            prefer_early=False,
            ideal_date=date(2026, 2, 14),
        )

        slot = Slot(
            config=SlotConfig(
                id=999,
                type="Bar Table",
                token="custom_token_12345",
            ),
            date=SlotDate(
                start=datetime(2026, 2, 14, 12, 0),
                end=datetime(2026, 2, 14, 13, 30),
            ),
        )

        body = build_get_slot_details_body(request, slot)

        assert body.config_id == "custom_token_12345"

    def test_party_size_from_request(self):
        """Should use party_size from reservation request."""
        request = ReservationRequest(
            venue_id="60058",
            party_size=6,
            ideal_hour=19,
            ideal_minute=0,
            window_hours=2,
            prefer_early=True,
            ideal_date=date(2026, 2, 14),
        )

        slot = Slot(
            config=SlotConfig(id=1, type="Dining", token="token"),
            date=SlotDate(
                start=datetime(2026, 2, 14, 19, 0),
                end=datetime(2026, 2, 14, 21, 0),
            ),
        )

        body = build_get_slot_details_body(request, slot)

        assert body.party_size == 6


class TestBuildAuthRequestBody:
    """Tests for build_auth_request_body function."""

    def test_builds_correct_structure(self):
        """Should create AuthRequestBody with email and password."""
        config = ResyConfig(
            api_key="test_api_key",
            token="test_token",
            payment_method_id=12345,
            email="test@example.com",
            password="secretpassword",
        )

        body = build_auth_request_body(config)

        assert body.email == "test@example.com"
        assert body.password == "secretpassword"

    def test_uses_config_credentials(self):
        """Should extract email and password from config."""
        config = ResyConfig(
            api_key="key",
            token="token",
            payment_method_id=1,
            email="user@resy.com",
            password="resypassword123",
        )

        body = build_auth_request_body(config)

        assert body.email == "user@resy.com"
        assert body.password == "resypassword123"


class TestBuildBookRequestBody:
    """Tests for build_book_request_body function."""

    def test_builds_correct_structure(self):
        """Should create BookRequestBody with correct fields."""
        details = DetailsResponseBody(
            book_token=BookToken(
                value="book_token_value_12345",
                date_expires=datetime(2026, 2, 14, 19, 35),
            )
        )

        config = ResyConfig(
            api_key="test_api_key",
            token="test_token",
            payment_method_id=99999,
        )

        body = build_book_request_body(details, config)

        assert body.book_token == "book_token_value_12345"
        assert body.struct_payment_method.id == 99999

    def test_uses_book_token_value(self):
        """Should extract book_token.value from details response."""
        details = DetailsResponseBody(
            book_token=BookToken(
                value="unique_booking_token_abc",
                date_expires=datetime(2026, 2, 14, 20, 0),
            )
        )

        config = ResyConfig(
            api_key="key",
            token="token",
            payment_method_id=1,
        )

        body = build_book_request_body(details, config)

        assert body.book_token == "unique_booking_token_abc"

    def test_uses_payment_method_from_config(self):
        """Should create PaymentMethod from config.payment_method_id."""
        details = DetailsResponseBody(
            book_token=BookToken(
                value="token",
                date_expires=datetime(2026, 2, 14, 20, 0),
            )
        )

        config = ResyConfig(
            api_key="key",
            token="token",
            payment_method_id=777888,
        )

        body = build_book_request_body(details, config)

        assert body.struct_payment_method.id == 777888

    def test_default_source_id(self):
        """Should have default source_id."""
        details = DetailsResponseBody(
            book_token=BookToken(
                value="token",
                date_expires=datetime(2026, 2, 14, 20, 0),
            )
        )

        config = ResyConfig(
            api_key="key",
            token="token",
            payment_method_id=1,
        )

        body = build_book_request_body(details, config)

        assert body.source_id == "resy.com-venue-details"
