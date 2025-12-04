import datetime as dt
import sys
import logging
from pathlib import Path

import pytest

# Setup logging BEFORE any other imports
# This must be done before importing main or resy_client modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force reconfiguration even if basicConfig was called before
)

# Allow importing main.py directly from the functions directory
sys.path.append(str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402

from resy_client.manager import ResyManager

logger = logging.getLogger(__name__)

# Ensure resy_client logger is at INFO level
logging.getLogger('resy_client.manager').setLevel(logging.INFO)


class DummyRequest:
    def __init__(self, json_body=None):
        self._json = json_body or {}
        self.args = {}

    def get_json(self, silent=False):
        return self._json


class FakeDocSnapshot:
    def __init__(self, data, exists=True):
        self._data = data
        self.exists = exists

    def to_dict(self):
        return self._data


class FakeDocRef:
    def __init__(self, snapshot):
        self._snapshot = snapshot
        self.updates = []

    def get(self):
        return self._snapshot

    def update(self, data):
        self.updates.append(data)


class FakeCollection:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.doc_ref = FakeDocRef(snapshot)
        self.document_calls = []

    def document(self, job_id):
        self.document_calls.append(job_id)
        return self.doc_ref


class FakeDB:
    def __init__(self, snapshot):
        self.collection_obj = FakeCollection(snapshot)
        self.collection_calls = []

    def collection(self, name):
        self.collection_calls.append(name)
        return self.collection_obj


def extract_body_and_status(response):
    if isinstance(response, tuple) and len(response) == 2:
        return response
    return response, None


def test_run_snipe_updates_job_on_success(monkeypatch, caplog):
    # Capture all logs
    caplog.set_level(logging.DEBUG)

    now = dt.datetime.now()
    token = "success-token"

    # Set drop time to 3 seconds in the future to actually test timing
    # This will let us verify the log fires at the exact right moment
    drop_time = now + dt.timedelta(seconds=3)
    drop_time_iso = drop_time.replace(microsecond=0).isoformat()

    job_data = {
        "jobId": "abc123",
        "partySize": 2,
        "venueId": "v1",
        "date": drop_time.date().isoformat(),
        "hour": 19,
        "minute": 0,
        "dropDate": drop_time.date().isoformat(),
        "dropHour": drop_time.hour,
        "dropMinute": drop_time.minute,
        "targetTimeIso": drop_time_iso,
    }

    fake_db = FakeDB(FakeDocSnapshot(job_data))
    monkeypatch.setattr(main, "get_db", lambda: fake_db)

    # Mock _get_drop_time to return drop_time (3 seconds in future)
    # This will make make_reservation_at_opening_time wait until that time
    monkeypatch.setattr(
        ResyManager,
        "_get_drop_time",
        lambda _self, _timed_req: dt.datetime.fromisoformat(drop_time.replace(microsecond=0).isoformat())
    )

    # Mock make_reservation_with_retries to avoid API calls
    # This lets make_reservation_at_opening_time execute and log
    monkeypatch.setattr(
        ResyManager,
        "make_reservation_with_retries",
        lambda _self, _reservation_request: token
    )

    # Record the time before calling run_snipe
    start_time = dt.datetime.now()

    response = main.run_snipe(DummyRequest({"jobId": job_data["jobId"]}))
    end_time = dt.datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    body, status = extract_body_and_status(response)

    # Print all captured logs
    print("\n=== CAPTURED LOGS ===")
    print(caplog.text)
    print("=== END LOGS ===\n")
    print(f"\n=== TIMING INFO ===")
    print(f"Expected drop time: {drop_time.isoformat()}")
    print(f"Actual elapsed time: {elapsed:.3f} seconds")
    print(f"Expected elapsed: ~3 seconds (accounting for run_snipe's targetTimeIso sleep)")
    print("=== END TIMING INFO ===\n")

    assert status in (None, 200)
    assert body["status"] == "done"
    assert body["jobId"] == job_data["jobId"]
    assert body["resyToken"] == token

    assert fake_db.collection_obj.doc_ref.updates, "Firestore should be updated"
    update_payload = fake_db.collection_obj.doc_ref.updates[-1]
    assert update_payload["status"] == "done"
    assert update_payload["resyToken"] == token
    assert "lastUpdate" in update_payload

    # Verify timing: should have taken approximately 3 seconds (with some tolerance)
    # The test should wait for the drop time before making the reservation
    assert elapsed >= 2, f"Expected to wait ~3 seconds, but only took {elapsed:.3f}s"
    assert elapsed <= 4.0, f"Expected to wait ~3 seconds, but took {elapsed:.3f}s"


def test_run_snipe_returns_404_for_missing_job(monkeypatch):
    fake_db = FakeDB(FakeDocSnapshot({}, exists=False))
    monkeypatch.setattr(main, "get_db", lambda: fake_db)
    monkeypatch.setattr(main.time, "sleep", lambda *args, **kwargs: None)

    response = main.run_snipe(DummyRequest({"jobId": "missing"}))
    body, status = extract_body_and_status(response)

    assert status == 404
    assert body["error"] == "Job not found"
    assert not fake_db.collection_obj.doc_ref.updates


if __name__ == "__main__":
    pytest.main([__file__])
