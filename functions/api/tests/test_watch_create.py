"""
Creating and editing watches through create_snipe / update_snipe. A watch must never
get a Cloud Scheduler job, and must be rejected when its range is unusable or a cap
would be broken, before anything is written.
"""
import datetime as dt
from unittest.mock import MagicMock

import pytest

from api import schedule
from api.constants import WATCH_MAX_PER_USER
from api.tests.watch_fakes import FakeDb, make_watch_doc

TOMORROW = (dt.date.today() + dt.timedelta(days=1)).isoformat()


@pytest.fixture(name="db")
def fixture_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(schedule, "get_db", lambda: db)
    scheduler = MagicMock()
    monkeypatch.setattr(schedule, "get_scheduler_client", lambda: scheduler)
    db.scheduler = scheduler
    return db


def body(**overrides) -> dict:
    data = {"watchMode": True, "userId": "user-1", "venueId": "443", "partySize": 2,
            "date": TOMORROW, "rangeStart": "17:00", "rangeEnd": "21:00"}
    data.update(overrides)
    return data


def status_of(response) -> int:
    return response[1] if isinstance(response, tuple) else 200


class TestCreateWatch:
    def test_creates_a_pending_watch_without_a_scheduler_job(self, db):
        response = schedule._create_watch(body())  # pylint: disable=protected-access
        assert status_of(response) == 200
        (job,) = db.docs("reservationJobs").values()
        assert job["watchMode"] is True
        assert job["status"] == "pending"
        assert (job["rangeStart"], job["rangeEnd"]) == ("17:00", "21:00")
        assert (job["hour"], job["minute"]) == (17, 0)
        assert "dropDate" not in job
        db.scheduler.create_job.assert_not_called()

    def test_time_is_normalized(self, db):
        schedule._create_watch(body(rangeStart="7:5", rangeEnd="9:00"))  # pylint: disable=protected-access
        (job,) = db.docs("reservationJobs").values()
        assert (job["rangeStart"], job["rangeEnd"]) == ("07:05", "09:00")

    @pytest.mark.parametrize("overrides,message", [
        ({"rangeStart": "21:00", "rangeEnd": "17:00"}, "before"),
        ({"date": "2020-01-01"}, "passed"),
        ({"rangeStart": "25:00"}, "Invalid"),
        ({"rangeEnd": None}, "Missing"),
    ])
    def test_unusable_range_is_rejected_before_writing(self, db, overrides, message):
        response = schedule._create_watch(body(**overrides))  # pylint: disable=protected-access
        assert status_of(response) == 400
        assert message in str(response)
        assert not db.docs("reservationJobs")

    def test_user_cap_is_enforced(self, db):
        for i in range(WATCH_MAX_PER_USER):
            db.collection("reservationJobs").document(f"w{i}").set(make_watch_doc(f"w{i}", venueId=str(i)))
        response = schedule._create_watch(body(venueId="999"))  # pylint: disable=protected-access
        assert status_of(response) == 400
        assert len(db.docs("reservationJobs")) == WATCH_MAX_PER_USER


class TestUpdateWatch:
    def test_edit_changes_range_and_reschedules_nothing(self, db):
        db.collection("reservationJobs").document("w1").set(make_watch_doc("w1", date=TOMORROW))
        ref = db.collection("reservationJobs").document("w1")
        response = schedule._update_watch(ref, db.docs("reservationJobs")["w1"],  # pylint: disable=protected-access
                                          {"rangeStart": "18:30", "rangeEnd": "22:00"})
        assert status_of(response) == 200
        job = db.docs("reservationJobs")["w1"]
        assert (job["rangeStart"], job["hour"], job["minute"]) == ("18:30", 18, 30)
        db.scheduler.create_job.assert_not_called()
        db.scheduler.delete_job.assert_not_called()

    def test_edit_to_an_inverted_range_is_rejected(self, db):
        db.collection("reservationJobs").document("w1").set(make_watch_doc("w1", date=TOMORROW))
        ref = db.collection("reservationJobs").document("w1")
        response = schedule._update_watch(ref, db.docs("reservationJobs")["w1"],  # pylint: disable=protected-access
                                          {"rangeEnd": "19:00"})
        assert status_of(response) == 400
        assert db.docs("reservationJobs")["w1"]["rangeEnd"] == "22:00"
