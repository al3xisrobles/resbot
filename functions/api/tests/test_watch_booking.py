"""
Booking for cancellation watches. What matters: a watch books the slot it was
assigned and nothing else, books at most once, keeps watching when it simply lost a
race, and stops (instead of retrying every minute forever) when booking cannot work.
"""
import datetime as dt
import json
import pathlib
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from api import watch_booking
from api.constants import WATCH_CLAIM_STALE_SECONDS, WATCH_MAX_BOOKING_FAILURES
from api.resy_client.constants import RESY_BASE_URL, ResyEndpoints
from api.resy_client.errors import (NoSlotsError, RateLimitError, ResyApiError, ResySessionExpiredError,
                                    ResyTransientError, SlotTakenError)
from api.resy_client.manager import ResyManager
from api.resy_client.models import ReservationRequest, ResyConfig
from api.tests.watch_fakes import FakeDb, claim_with_fake_db, make_watch_doc

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "resy"
NOW = dt.datetime(2026, 9, 23, 21, 0, 50, tzinfo=dt.timezone.utc)


@pytest.fixture(name="db")
def fixture_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(watch_booking, "_claim", lambda _db, job_id, now: claim_with_fake_db(db, job_id, now))
    db.collection("reservationJobs").document("job-1").set(make_watch_doc("job-1"))
    return db


@pytest.fixture(name="user_manager")
def fixture_user_manager(monkeypatch):
    """The watcher's own manager, talking to a mocked Resy with a real user token."""
    config = ResyConfig(api_key="key", token="user-token", payment_method_id=1)
    request = ReservationRequest(venue_id="443", party_size=2, ideal_hour=20, ideal_minute=0,
                                 window_hours=1, prefer_early=False, ideal_date=dt.date(2026, 9, 25))
    monkeypatch.setattr(watch_booking, "_build_reservation_request_from_dict",
                        lambda job, user_id: (request, ResyManager.build(config)))
    monkeypatch.setattr("api.resy_client.http_client.time.sleep", lambda _s: None)


def mock_find_details_book():
    responses.add(responses.POST, RESY_BASE_URL + ResyEndpoints.FIND.value,
                  json=json.loads((FIXTURES / "find_available.json").read_text()))
    responses.add(responses.GET, RESY_BASE_URL + ResyEndpoints.DETAILS.value,
                  json={"book_token": {"value": "bt", "date_expires": "2026-09-23T22:00:00Z"}})
    responses.add(responses.POST, RESY_BASE_URL + ResyEndpoints.BOOK.value, json={"resy_token": "resy-123"})


class TestClaimAvailable:
    def test_pending_unclaimed_watch_can_be_claimed(self):
        assert watch_booking.claim_available({"status": "pending"}, NOW)

    def test_live_claim_blocks_a_second_booking(self):
        """Two overlapping ticks must not both book the same watch."""
        job = {"status": "pending", "bookingClaimedAt": NOW - dt.timedelta(seconds=5)}
        assert not watch_booking.claim_available(job, NOW)

    def test_stale_claim_from_a_crashed_tick_can_be_taken_over(self):
        job = {"status": "pending",
               "bookingClaimedAt": NOW - dt.timedelta(seconds=WATCH_CLAIM_STALE_SECONDS + 1)}
        assert watch_booking.claim_available(job, NOW)

    def test_finished_watch_is_never_claimed(self):
        for status in ("done", "failed", "cancelled"):
            assert not watch_booking.claim_available({"status": status}, NOW)


class TestClassifyError:
    @pytest.mark.parametrize("error,outcome", [
        (ResySessionExpiredError("expired", 419), watch_booking.AUTH),
        (NoSlotsError("gone"), watch_booking.GONE),
        (SlotTakenError("taken"), watch_booking.GONE),
        (ResyApiError("conflict", status_code=412), watch_booking.GONE),
        (RateLimitError("slow down"), watch_booking.TRANSIENT),
        (ResyTransientError("503", 503), watch_booking.TRANSIENT),
        (requests.exceptions.ConnectionError("reset"), watch_booking.TRANSIENT),
        (ResyApiError("payment method required", status_code=402), watch_booking.FAILURE),
        (ValueError("unexpected"), watch_booking.FAILURE),
    ])
    def test_outcomes(self, error, outcome):
        assert watch_booking.classify_error(error) == outcome


class TestAttemptBooking:
    @responses.activate
    @pytest.mark.usefixtures("user_manager")
    def test_books_the_assigned_slot_and_finishes_the_watch(self, db):
        mock_find_details_book()
        assert watch_booking.attempt_booking(db, "job-1", "21:30|Dining Room", NOW) == watch_booking.BOOKED
        job = db.docs("reservationJobs")["job-1"]
        assert job["status"] == "done"
        assert job["resyToken"] == "resy-123"
        assert job["bookingClaimedAt"] is None
        details_call = next(c for c in responses.calls if ResyEndpoints.DETAILS.value in c.request.url)
        slot_tokens = {s["date"]["start"][11:16]: s["config"]["token"] for s in
                       json.loads((FIXTURES / "find_available.json").read_text())["results"]["venues"][0]["slots"]}
        # The booking token was requested for the 21:30 slot, not whatever a selector would pick.
        config_id = parse_qs(urlparse(details_call.request.url).query)["config_id"][0]
        assert config_id == slot_tokens["21:30"]

    @responses.activate
    @pytest.mark.usefixtures("user_manager")
    def test_booking_uses_the_watchers_token_not_the_poller(self, db):
        mock_find_details_book()
        watch_booking.attempt_booking(db, "job-1", "21:30|Dining Room", NOW)
        assert all(c.request.headers["X-Resy-Auth-Token"] == "user-token" for c in responses.calls)

    @responses.activate
    @pytest.mark.usefixtures("user_manager")
    def test_vanished_slot_keeps_watching(self, db):
        mock_find_details_book()
        assert watch_booking.attempt_booking(db, "job-1", "19:00|Bar", NOW) == watch_booking.GONE
        job = db.docs("reservationJobs")["job-1"]
        assert job["status"] == "pending"
        assert job["bookingClaimedAt"] is None
        assert job["bookingFailures"] == 0
        assert not any(ResyEndpoints.BOOK.value in c.request.url for c in responses.calls)

    @responses.activate
    @pytest.mark.usefixtures("user_manager")
    def test_expired_session_ends_the_watch(self, db):
        responses.add(responses.POST, RESY_BASE_URL + ResyEndpoints.FIND.value, status=419,
                      json={"message": "Unauthorized"})
        assert watch_booking.attempt_booking(db, "job-1", "21:30|Dining Room", NOW) == watch_booking.AUTH
        job = db.docs("reservationJobs")["job-1"]
        assert job["status"] == "failed"
        assert "reconnect" in job["errorMessage"]

    @responses.activate
    @pytest.mark.usefixtures("user_manager")
    def test_repeated_failures_end_the_watch(self, db):
        """A venue that rejects our payment method would otherwise be retried every minute forever."""
        for attempt in range(1, WATCH_MAX_BOOKING_FAILURES + 1):
            responses.reset()
            responses.add(responses.POST, RESY_BASE_URL + ResyEndpoints.FIND.value,
                          json=json.loads((FIXTURES / "find_available.json").read_text()))
            responses.add(responses.GET, RESY_BASE_URL + ResyEndpoints.DETAILS.value, status=402,
                          json={"message": "Payment method required"})
            outcome = watch_booking.attempt_booking(db, "job-1", "21:30|Dining Room",
                                                    NOW + dt.timedelta(minutes=attempt))
            assert outcome == watch_booking.FAILURE
            job = db.docs("reservationJobs")["job-1"]
            expected = "failed" if attempt == WATCH_MAX_BOOKING_FAILURES else "pending"
            assert job["status"] == expected
        assert job["bookingFailures"] == WATCH_MAX_BOOKING_FAILURES

    def test_second_attempt_while_claimed_does_nothing(self, db):
        db.collection("reservationJobs").document("job-1").update({"bookingClaimedAt": NOW})
        assert watch_booking.attempt_booking(db, "job-1", "21:30|Dining Room", NOW) is None


class TestBookingFlag:
    def test_booking_is_off_unless_explicitly_enabled(self, monkeypatch):
        monkeypatch.delenv("WATCH_BOOKING_ENABLED", raising=False)
        assert not watch_booking.booking_enabled()
        monkeypatch.setenv("WATCH_BOOKING_ENABLED", "yes")
        assert not watch_booking.booking_enabled()
        monkeypatch.setenv("WATCH_BOOKING_ENABLED", "true")
        assert watch_booking.booking_enabled()
