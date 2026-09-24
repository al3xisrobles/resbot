"""
The watch tick against real captured Resy payloads (fixtures/resy, refreshed by
scripts/capture_resy_fixtures.py) and replayed failure sequences.

What these protect: one poll per watched date however many people watch it, polls only
on resbot's own account, one bad target never stalls the rest, a bot block is backed
away from rather than hammered, and the tick chain never skips or forks a minute.
"""
import copy
import datetime as dt
import json
import pathlib

import pytest
import requests
import responses

from api import watch
from api.resy_client.constants import RESY_BASE_URL, ResyEndpoints
from api.tests.watch_fakes import FakeDb, make_watch_doc

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "resy"
FIND_URL = RESY_BASE_URL + ResyEndpoints.FIND.value
AUTH_URL = RESY_BASE_URL + ResyEndpoints.PASSWORD_AUTH.value
POLL_TOKEN = "poll-account-token"
# 5:00:50pm Eastern on 2026-09-23: outside quiet hours, before every watch's range ends
NOW = dt.datetime(2026, 9, 23, 21, 0, 50, tzinfo=dt.timezone.utc)
WATCH_DATE = "2026-09-25"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def find_with_quantity(slot_time: str, quantity: int) -> dict:
    """The real captured find payload with one slot's table count changed."""
    body = copy.deepcopy(load("find_available.json"))
    for slot in body["results"]["venues"][0]["slots"]:
        if slot["date"]["start"].endswith(slot_time):
            slot["quantity"] = quantity
    return body


def auth_body(token: str = POLL_TOKEN) -> dict:
    return {"token": token, "payment_methods": []}


@pytest.fixture(autouse=True)
def _quiet_env(monkeypatch):
    monkeypatch.delenv("WATCH_BOOKING_ENABLED", raising=False)
    monkeypatch.setenv("RESY_POLL_EMAIL", "poller@example.com")
    monkeypatch.setenv("RESY_POLL_PASSWORD", "poller-password")
    monkeypatch.setattr(watch, "_poll_token", POLL_TOKEN)  # most tests start signed in
    monkeypatch.setattr(watch, "_login_blocked_until", None)
    monkeypatch.setattr("api.resy_client.http_client.time.sleep", lambda _s: None)


@pytest.fixture(name="db")
def fixture_db():
    db = FakeDb()
    db.collection("reservationJobs").document("job-1").set(make_watch_doc("job-1"))
    return db


def add_watch(db: FakeDb, job_id: str, **overrides) -> None:
    db.collection("reservationJobs").document(job_id).set(make_watch_doc(job_id, **overrides))


def only_venue(venue_id: int):
    return [responses.matchers.json_params_matcher(
        {"lat": 0, "long": 0, "day": WATCH_DATE, "party_size": 2, "venue_id": venue_id})]


EMPTY_STATS = {k: 0 for k in ("watches", "targets", "find_calls", "openings", "assignments", "bookings",
                              "rate_limited", "blocked", "errors", "skipped_backoff", "auth_errors")}


def calls_to(url: str):
    return [c for c in responses.calls if c.request.url.startswith(url)]


def target_slots(db: FakeDb, target: str = "443_2") -> dict:
    return db.docs("watchTargets")[target]["slots"]


class TestPolling:
    @responses.activate
    def test_two_watchers_on_one_date_share_one_find_call(self, db):
        add_watch(db, "job-2", userId="user-2")
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        stats = watch.run_tick(db, NOW)
        assert stats["targets"] == 1
        assert len(calls_to(FIND_URL)) == 1

    @responses.activate
    def test_each_watched_date_costs_one_find_call(self, db):
        add_watch(db, "job-2", date="2026-09-26")
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        assert watch.run_tick(db, NOW)["find_calls"] == 2

    @responses.activate
    def test_polls_never_touch_the_calendar(self, db):
        """Resy's bot block hit /4/venue/calendar while /4/find kept working."""
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW)
        assert all(ResyEndpoints.CALENDAR.value not in c.request.url for c in responses.calls)

    @responses.activate
    def test_polls_use_only_the_poll_account(self, db, monkeypatch):
        """
        Steady polling is what gets accounts banned, so it must only ever run on resbot's
        own account: never a watcher's, and never the owner's RESY_TOKEN.
        """
        monkeypatch.setenv("RESY_TOKEN", "owner-token")
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        watch.run_tick(db, NOW)
        assert responses.calls
        for call in responses.calls:
            assert call.request.headers["X-Resy-Auth-Token"] == POLL_TOKEN
            assert call.request.headers["X-Resy-Universal-Auth"] == POLL_TOKEN

    @responses.activate
    def test_sold_out_date_is_an_empty_snapshot(self, db):
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW)
        assert target_slots(db) == {WATCH_DATE: {}}

    @responses.activate
    def test_snapshot_records_table_counts(self, db):
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        watch.run_tick(db, NOW)
        assert target_slots(db) == {WATCH_DATE: {"21:15|Dining Room": 1, "21:30|Dining Room": 2}}


class TestOpenings:
    @responses.activate
    def test_first_poll_is_a_baseline_then_new_slots_are_openings(self, db):
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW)
        assert not db.docs("watchEvents")

        responses.replace(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["openings"] == 2
        events = sorted(db.docs("watchEvents").values(), key=lambda e: e["slotKey"])
        assert [e["slotKey"] for e in events] == ["21:15|Dining Room", "21:30|Dining Room"]
        # In shadow mode the event still records who would have booked it.
        assert events[0]["assignedJobIds"] == ["job-1"]
        assert events[0]["bookingEnabled"] is False

    @responses.activate
    def test_extra_table_at_a_shown_time_is_an_opening(self, db):
        """A cancellation at a time that still had a table left only shows up as a higher quantity."""
        responses.add(responses.POST, FIND_URL, json=find_with_quantity("21:30:00", 1))
        watch.run_tick(db, NOW)
        responses.replace(responses.POST, FIND_URL, json=find_with_quantity("21:30:00", 2))
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["openings"] == 1
        (event,) = db.docs("watchEvents").values()
        assert (event["slotKey"], event["quantity"]) == ("21:30|Dining Room", 2)

    @responses.activate
    def test_slot_that_vanishes_and_returns_is_an_opening_again(self, db):
        """The stored snapshot must drop vanished slots, or their return would be missed."""
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        watch.run_tick(db, NOW)
        responses.replace(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert target_slots(db) == {WATCH_DATE: {}}
        responses.replace(responses.POST, FIND_URL, json=load("find_available.json"))
        assert watch.run_tick(db, NOW + dt.timedelta(minutes=2))["openings"] == 2

    @responses.activate
    def test_snapshot_from_before_quantities_is_a_baseline(self, db):
        """The first tick after deploying must not log every open slot as an opening."""
        db.collection("watchTargets").document("443_2").set(
            {"slots": {WATCH_DATE: ["21:15|Dining Room"]}, "backoffUntil": None})
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        assert watch.run_tick(db, NOW)["openings"] == 0


class TestBookingModes:
    @responses.activate
    def test_shadow_mode_never_books(self, db, monkeypatch):
        attempts = []
        monkeypatch.setattr(watch, "attempt_booking", lambda *a: attempts.append(a))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW)
        assert stats["assignments"] == 1
        assert not attempts

    @responses.activate
    def test_booking_mode_books_the_assignment_including_already_open_slots(self, db, monkeypatch):
        """A watch created on a date that already has a matching slot books it on the next tick."""
        attempts = []
        monkeypatch.setenv("WATCH_BOOKING_ENABLED", "true")
        monkeypatch.setattr(watch, "attempt_booking",
                            lambda _db, job_id, key, _now: attempts.append((job_id, key)) or "booked")
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW)
        assert attempts == [("job-1", "21:15|Dining Room")]
        assert stats["bookings"] == 1

    @responses.activate
    def test_out_of_range_slots_are_not_assigned(self, db):
        add_watch(db, "job-1", rangeStart="17:00", rangeEnd="19:00")
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        assert watch.run_tick(db, NOW)["assignments"] == 0


class TestFailures:
    @responses.activate
    def test_rate_limited_target_backs_off_without_failing_others(self, db):
        add_watch(db, "job-2", venueId="53342")
        responses.add(responses.POST, FIND_URL, status=429, headers={"Retry-After": "120"}, match=only_venue(443))
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"), match=only_venue(53342))
        stats = watch.run_tick(db, NOW)
        assert stats["rate_limited"] == 1
        assert stats["find_calls"] == 2
        assert db.docs("watchTargets")["443_2"]["backoffUntil"] >= NOW + dt.timedelta(seconds=120)
        assert db.docs("watchTargets")["53342_2"]["backoffUntil"] is None

        # While backed off, the target costs no requests at all.
        responses.calls.reset()  # pylint: disable=no-member
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["skipped_backoff"] == 1
        assert all(b'"venue_id": 443' not in (c.request.body or b"") for c in responses.calls)

    @responses.activate
    def test_long_retry_after_does_not_sleep_inside_the_tick(self, db, monkeypatch):
        """A Retry-After past the tick's timeout must back off, not sleep until the tick is killed."""
        slept = []
        monkeypatch.setattr("api.resy_client.http_client.time.sleep", slept.append)
        responses.add(responses.POST, FIND_URL, status=429, headers={"Retry-After": "300"})
        watch.run_tick(db, NOW)
        assert len(calls_to(FIND_URL)) == 1
        assert not slept

    @responses.activate
    def test_bot_block_500_backs_off_instead_of_hammering(self, db):
        """
        Once Resy's bot protection trips it answers 500 for an hour or more. Retrying, or
        calling again next minute, only keeps it tripped: one call, then stay away.
        """
        responses.add(responses.POST, FIND_URL, status=500)
        stats = watch.run_tick(db, NOW)
        assert stats["blocked"] == 1
        assert len(calls_to(FIND_URL)) == 1
        backoff = db.docs("watchTargets")["443_2"]["backoffUntil"]
        assert backoff == NOW + dt.timedelta(seconds=watch.WATCH_TARGET_BLOCK_BACKOFF_SECONDS)

        for minute in range(1, 10):
            assert watch.run_tick(db, NOW + dt.timedelta(minutes=minute))["skipped_backoff"] == 1
        assert len(calls_to(FIND_URL)) == 1

    @responses.activate
    def test_connection_reset_on_one_target_leaves_others_polled(self, db):
        add_watch(db, "job-2", venueId="53342")
        responses.add(responses.POST, FIND_URL, body=requests.exceptions.ConnectionError("reset"),
                      match=only_venue(443))
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"), match=only_venue(53342))
        stats = watch.run_tick(db, NOW)
        assert stats["errors"] == 1
        assert "53342_2" in db.docs("watchTargets")

    @responses.activate
    def test_schema_drift_is_an_error_not_a_silent_empty_poll(self, db):
        """If Resy changes the find shape, we must hear about it rather than see 'no slots' forever."""
        responses.add(responses.POST, FIND_URL, json={"results": {"hotels": []}})
        stats = watch.run_tick(db, NOW)
        assert stats["errors"] == 1


class TestLifecycle:
    def test_watch_past_its_range_end_is_expired(self, db):
        add_watch(db, "job-old", date="2026-09-23", rangeEnd="16:30")  # 4:30pm ET, before NOW
        live = watch.expire_watches(db, watch.load_active_watches(db), NOW)
        assert [w["jobId"] for w in live] == ["job-1"]
        assert db.docs("reservationJobs")["job-old"]["status"] == "failed"

    def test_successor_comes_from_scheduled_time_not_the_clock(self, monkeypatch):
        """A tick scheduled for :50 that starts late must still queue the next minute's :50."""
        queued = []
        monkeypatch.setattr(watch, "enqueue_tick", queued.append)
        monkeypatch.setattr(watch, "run_tick", lambda *_a: dict(EMPTY_STATS))
        scheduled = dt.datetime(2026, 9, 23, 20, 0, 50, tzinfo=dt.timezone.utc)
        watch.process_tick(scheduled, scheduled + dt.timedelta(seconds=12), db=FakeDb())
        assert queued == [dt.datetime(2026, 9, 23, 20, 1, 50, tzinfo=dt.timezone.utc)]

    def test_successor_is_queued_even_if_the_poll_crashes(self, monkeypatch):
        queued = []
        monkeypatch.setattr(watch, "enqueue_tick", queued.append)

        def crash(*_a):
            raise RuntimeError("boom")
        monkeypatch.setattr(watch, "run_tick", crash)
        watch.process_tick(NOW, NOW, db=FakeDb())
        assert len(queued) == 1

    def test_quiet_hours_stop_the_chain(self, monkeypatch):
        queued, polled = [], []
        monkeypatch.setattr(watch, "enqueue_tick", queued.append)
        monkeypatch.setattr(watch, "run_tick", lambda *a: polled.append(a))
        three_am_eastern = dt.datetime(2026, 9, 23, 7, 0, 50, tzinfo=dt.timezone.utc)
        assert watch.process_tick(three_am_eastern, three_am_eastern, db=FakeDb()) is None
        assert not queued
        assert not polled

    def test_last_tick_before_quiet_hours_does_not_queue_into_them(self, monkeypatch):
        queued = []
        monkeypatch.setattr(watch, "enqueue_tick", queued.append)
        monkeypatch.setattr(watch, "run_tick", lambda *_a: dict(EMPTY_STATS))
        one_59_eastern = dt.datetime(2026, 9, 23, 5, 59, 50, tzinfo=dt.timezone.utc)
        watch.process_tick(one_59_eastern, one_59_eastern, db=FakeDb())
        assert not queued

    def test_task_id_is_one_per_minute(self):
        """Same minute, same ID: Cloud Tasks rejects the duplicate, so the chain cannot fork."""
        a = dt.datetime(2026, 9, 23, 20, 1, 50, tzinfo=dt.timezone.utc)
        assert watch.tick_task_id(a) == watch.tick_task_id(a.replace(second=10))
        assert watch.tick_task_id(a) != watch.tick_task_id(a + dt.timedelta(minutes=1))

    def test_seed_time_lands_on_the_tick_second(self):
        now = dt.datetime(2026, 9, 23, 20, 1, 49, tzinfo=dt.timezone.utc)
        assert watch.next_seed_time(now) == dt.datetime(2026, 9, 23, 20, 2, 50, tzinfo=dt.timezone.utc)
        early = now.replace(second=10)
        assert watch.next_seed_time(early) == early.replace(second=50)


class TestEnqueue:
    def test_credential_is_refreshed_before_the_task_is_built(self, monkeypatch):
        """
        On Cloud Run the credential's email reads "default" until refreshed, and a task
        built with that email is rejected by Cloud Tasks. The real email must be in
        place by the time firebase-admin builds the task.
        """
        class Credential:
            service_account_email = "default"

            def refresh(self, _request):
                self.service_account_email = "782094781658-compute@developer.gserviceaccount.com"

        credential = Credential()
        app = type("App", (), {"credential": type("Cred", (), {"get_credential": lambda _self: credential})()})()
        monkeypatch.setattr(watch.firebase_admin, "get_app", lambda: app)
        emails_at_enqueue = []

        class Queue:
            def enqueue(self, _data, _opts):
                emails_at_enqueue.append(credential.service_account_email)

        monkeypatch.setattr(watch.fb_functions, "task_queue", lambda _name: Queue())
        assert watch.enqueue_tick(NOW) is True
        assert emails_at_enqueue == ["782094781658-compute@developer.gserviceaccount.com"]

    def test_duplicate_minute_is_not_an_error(self, monkeypatch):
        class Credential:
            service_account_email = "sa@example.com"

        app = type("App", (), {"credential": type("Cred", (), {"get_credential": lambda _self: Credential()})()})()
        monkeypatch.setattr(watch.firebase_admin, "get_app", lambda: app)

        class Queue:
            def enqueue(self, _data, _opts):
                raise watch.fb_exceptions.AlreadyExistsError("exists", None)

        monkeypatch.setattr(watch.fb_functions, "task_queue", lambda _name: Queue())
        assert watch.enqueue_tick(NOW) is False

    def test_task_body_is_what_the_tasks_handler_accepts(self, monkeypatch):
        """
        The tasks handler rejects any body that is not exactly {"data": ...} with a 400,
        and the Python Admin SDK does not add that wrapper, so every tick would fail.
        """
        from firebase_functions.private import util as fn_util  # pylint: disable=import-outside-toplevel

        class Credential:
            service_account_email = "sa@example.com"

        app = type("App", (), {"credential": type("Cred", (), {"get_credential": lambda _self: Credential()})()})()
        monkeypatch.setattr(watch.firebase_admin, "get_app", lambda: app)
        sent = []

        class Queue:
            def enqueue(self, data, _opts):
                sent.append(data)

        monkeypatch.setattr(watch.fb_functions, "task_queue", lambda _name: Queue())
        watch.enqueue_tick(NOW)
        request = type("Req", (), {"json": sent[0]})()
        assert fn_util._on_call_valid_body(request)  # pylint: disable=protected-access
        assert watch._parse_scheduled_for(sent[0]["data"]["scheduledFor"], NOW) == NOW  # pylint: disable=protected-access


class TestPollAccount:
    @responses.activate
    def test_signs_in_once_and_reuses_the_session(self, db, monkeypatch):
        monkeypatch.setattr(watch, "_poll_token", None)
        responses.add(responses.POST, AUTH_URL, json=auth_body())
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW)
        watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert len(calls_to(AUTH_URL)) == 1
        assert all(c.request.headers["X-Resy-Auth-Token"] == POLL_TOKEN for c in calls_to(FIND_URL))

    @responses.activate
    def test_rejected_session_signs_in_again_next_tick(self, db):
        responses.add(responses.POST, FIND_URL, status=419, json={"message": "Unauthorized"})
        stats = watch.run_tick(db, NOW)
        assert stats["auth_errors"] == 1
        assert watch._poll_token is None  # pylint: disable=protected-access

        responses.replace(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        responses.add(responses.POST, AUTH_URL, json=auth_body("fresh-token"))
        watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert calls_to(FIND_URL)[-1].request.headers["X-Resy-Auth-Token"] == "fresh-token"

    @responses.activate
    def test_failed_sign_in_is_not_retried_every_minute(self, db, monkeypatch):
        """A wrong password retried every minute is its own way to get the account locked."""
        monkeypatch.setattr(watch, "_poll_token", None)
        responses.add(responses.POST, AUTH_URL, status=419, json={"message": "Unauthorized"})
        with pytest.raises(Exception):
            watch.run_tick(db, NOW)
        with pytest.raises(RuntimeError, match="paused"):
            watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert len(calls_to(AUTH_URL)) == 1
        assert not calls_to(FIND_URL)

    def test_missing_credentials_fail_loudly(self, db, monkeypatch):
        """Without the poll account, never fall back to signed-out or someone else's token."""
        monkeypatch.setattr(watch, "_poll_token", None)
        monkeypatch.delenv("RESY_POLL_PASSWORD")
        with pytest.raises(RuntimeError, match="RESY_POLL_EMAIL"):
            watch.run_tick(db, NOW)
