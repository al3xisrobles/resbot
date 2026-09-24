"""
The watch tick against real captured Resy payloads (fixtures/resy, refreshed by
scripts/capture_resy_fixtures.py) and replayed failure sequences.

What these protect: one poll per target however many people watch it, no user token
on any poll, one bad target never stalls the rest, and the tick chain never skips or
forks a minute.
"""
import copy
import datetime as dt
import json
import pathlib

import pytest
import requests
import responses
from responses import registries

from api import watch
from api.resy_client.constants import RESY_BASE_URL, ResyEndpoints
from api.tests.watch_fakes import FakeDb, make_watch_doc

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "resy"
CALENDAR_URL = RESY_BASE_URL + ResyEndpoints.CALENDAR.value
FIND_URL = RESY_BASE_URL + ResyEndpoints.FIND.value
# 5:00:50pm Eastern on 2026-09-23: outside quiet hours, before every watch's range ends
NOW = dt.datetime(2026, 9, 23, 21, 0, 50, tzinfo=dt.timezone.utc)
WATCH_DATE = "2026-09-25"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def calendar_with(statuses: dict) -> dict:
    """The real captured calendar, with chosen dates' reservation status overridden."""
    body = copy.deepcopy(load("calendar.json"))
    for entry in body["scheduled"]:
        if entry["date"] in statuses:
            entry["inventory"]["reservation"] = statuses[entry["date"]]
    return body


@pytest.fixture(autouse=True)
def _quiet_env(monkeypatch):
    monkeypatch.delenv("WATCH_BOOKING_ENABLED", raising=False)
    monkeypatch.setattr("api.resy_client.http_client.time.sleep", lambda _s: None)


@pytest.fixture(name="db")
def fixture_db():
    db = FakeDb()
    db.collection("reservationJobs").document("job-1").set(make_watch_doc("job-1"))
    return db


def add_watch(db: FakeDb, job_id: str, **overrides) -> None:
    db.collection("reservationJobs").document(job_id).set(make_watch_doc(job_id, **overrides))


def only_venue(venue_id: str):
    return [responses.matchers.query_param_matcher(
        {"venue_id": venue_id, "num_seats": "2", "start_date": WATCH_DATE, "end_date": WATCH_DATE})]


EMPTY_STATS = {k: 0 for k in ("watches", "targets", "calendar_calls", "find_calls", "openings", "assignments",
                              "bookings", "rate_limited", "errors", "skipped_backoff")}


def calls_to(url: str):
    return [c for c in responses.calls if c.request.url.startswith(url)]


class TestPolling:
    @responses.activate
    def test_two_watchers_on_one_target_share_one_calendar_call(self, db):
        add_watch(db, "job-2", userId="user-2")
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({}))
        stats = watch.run_tick(db, NOW)
        assert stats["targets"] == 1
        assert len(calls_to(CALENDAR_URL)) == 1

    @responses.activate
    def test_polls_never_carry_a_user_token(self, db, monkeypatch):
        """Polling on a real account is what gets accounts banned; even RESY_TOKEN must not leak in."""
        monkeypatch.setenv("RESY_TOKEN", "owner-token")
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        watch.run_tick(db, NOW)
        assert responses.calls
        for call in responses.calls:
            assert call.request.headers["X-Resy-Auth-Token"] == ""
            assert call.request.headers["X-Resy-Universal-Auth"] == ""

    @responses.activate
    def test_sold_out_dates_cost_no_find_call(self, db):
        responses.add(responses.GET, CALENDAR_URL, json=load("calendar.json"))  # captured: all sold out
        stats = watch.run_tick(db, NOW)
        assert stats["find_calls"] == 0
        assert not calls_to(FIND_URL)
        assert db.docs("watchTargets")["443_2"]["slots"] == {WATCH_DATE: []}

    @responses.activate
    def test_available_date_is_found_and_snapshotted(self, db):
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        watch.run_tick(db, NOW)
        assert db.docs("watchTargets")["443_2"]["slots"][WATCH_DATE] == ["21:15|Dining Room", "21:30|Dining Room"]


class TestOpenings:
    @responses.activate
    def test_first_poll_is_a_baseline_then_new_slots_are_openings(self, db):
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_sold_out.json"))
        watch.run_tick(db, NOW)
        assert not db.docs("watchEvents")

        responses.replace(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["openings"] == 2
        events = sorted(db.docs("watchEvents").values(), key=lambda e: e["slotKey"])
        assert [e["slotKey"] for e in events] == ["21:15|Dining Room", "21:30|Dining Room"]
        # In shadow mode the event still records who would have booked it.
        assert events[0]["assignedJobId"] == "job-1"
        assert events[0]["bookingEnabled"] is False

    @responses.activate
    def test_slot_reopening_after_a_sell_out_is_an_opening(self, db):
        responses.add(responses.GET, CALENDAR_URL, json=load("calendar.json"))
        watch.run_tick(db, NOW)
        responses.replace(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["openings"] == 2


class TestBookingModes:
    @responses.activate
    def test_shadow_mode_never_books(self, db, monkeypatch):
        attempts = []
        monkeypatch.setattr(watch, "attempt_booking", lambda *a: attempts.append(a))
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
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
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        stats = watch.run_tick(db, NOW)
        assert attempts == [("job-1", "21:15|Dining Room")]
        assert stats["bookings"] == 1

    @responses.activate
    def test_out_of_range_slots_are_not_assigned(self, db):
        add_watch(db, "job-1", rangeStart="17:00", rangeEnd="19:00")
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
        responses.add(responses.POST, FIND_URL, json=load("find_available.json"))
        assert watch.run_tick(db, NOW)["assignments"] == 0


class TestFailures:
    @responses.activate
    def test_rate_limited_target_backs_off_without_failing_others(self, db):
        add_watch(db, "job-2", venueId="53342")
        responses.add(responses.GET, CALENDAR_URL, status=429, headers={"Retry-After": "120"},
                      match=only_venue("443"))
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({}), match=only_venue("53342"))
        stats = watch.run_tick(db, NOW)
        assert stats["rate_limited"] == 1
        assert stats["calendar_calls"] == 2
        backoff = db.docs("watchTargets")["443_2"]["backoffUntil"]
        assert backoff >= NOW + dt.timedelta(seconds=120)
        assert db.docs("watchTargets")["53342_2"]["backoffUntil"] is None

        # While backed off, the target costs no requests at all.
        responses.calls.reset()  # pylint: disable=no-member
        stats = watch.run_tick(db, NOW + dt.timedelta(minutes=1))
        assert stats["skipped_backoff"] == 1
        assert all("venue_id=443" not in c.request.url for c in responses.calls)

    @responses.activate
    def test_long_retry_after_does_not_sleep_inside_the_tick(self, db, monkeypatch):
        """A Retry-After past the tick's timeout must back off, not sleep until the tick is killed."""
        slept = []
        monkeypatch.setattr("api.resy_client.http_client.time.sleep", slept.append)
        responses.add(responses.GET, CALENDAR_URL, status=429, headers={"Retry-After": "300"})
        watch.run_tick(db, NOW)
        assert len(calls_to(CALENDAR_URL)) == 1
        assert not slept

    def test_transient_500s_are_retried_within_the_tick(self, db):
        with responses.RequestsMock(registry=registries.OrderedRegistry) as mock:
            mock.add(responses.GET, CALENDAR_URL, status=500)
            mock.add(responses.GET, CALENDAR_URL, status=500)
            mock.add(responses.GET, CALENDAR_URL, json=calendar_with({}))
            stats = watch.run_tick(db, NOW)
        assert stats["errors"] == 0
        assert "443_2" in db.docs("watchTargets")

    @responses.activate
    def test_connection_reset_on_one_target_leaves_others_polled(self, db):
        add_watch(db, "job-2", venueId="53342")
        responses.add(responses.GET, CALENDAR_URL, body=requests.exceptions.ConnectionError("reset"),
                      match=only_venue("443"))
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({}), match=only_venue("53342"))
        stats = watch.run_tick(db, NOW)
        assert stats["errors"] == 1
        assert "53342_2" in db.docs("watchTargets")
        # The reset was retried before giving up on that target.
        assert sum("venue_id=443" in c.request.url for c in responses.calls) == 3

    @responses.activate
    def test_schema_drift_is_an_error_not_a_silent_empty_poll(self, db):
        """If Resy changes the find shape, we must hear about it rather than see 'no slots' forever."""
        responses.add(responses.GET, CALENDAR_URL, json=calendar_with({WATCH_DATE: "available"}))
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
