"""
A minimal in-memory stand-in for the Firestore calls the watch code makes:
document get/set/update, equality where-queries, and batches. Transactions are not
faked; tests patch watch_booking._claim instead (see claim_with_fake_db).
"""
from __future__ import annotations

import copy
import datetime as dt
import itertools
from typing import Any, Dict, Optional

from google.cloud.firestore_v1.transforms import ArrayUnion

from api import watch_booking

_ids = itertools.count(1)


class FakeSnapshot:
    def __init__(self, data: Optional[dict]):
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[dict]:
        return copy.deepcopy(self._data)


class FakeDocRef:
    def __init__(self, store: Dict[str, dict], doc_id: str):
        self._store = store
        self.id = doc_id

    def get(self, **_kwargs) -> FakeSnapshot:
        return FakeSnapshot(self._store.get(self.id))

    def set(self, data: dict, merge=False) -> None:
        """
        Mirrors Firestore: merge=True deep-merges nested maps, merge=[fields] replaces the
        listed top-level fields whole, and no merge replaces the document.
        """
        current = copy.deepcopy(self._store.get(self.id, {})) if merge else {}
        if merge is True:
            self._store[self.id] = _deep_merge(current, data)
        elif merge:
            self._store[self.id] = _apply(current, {k: v for k, v in data.items() if k in merge})
        else:
            self._store[self.id] = _apply(current, data)

    def update(self, data: dict) -> None:
        if self.id not in self._store:
            raise KeyError(f"No document {self.id}")
        self._store[self.id] = _apply(self._store[self.id], data)


def _deep_merge(current: dict, data: dict) -> dict:
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            current[key] = _deep_merge(current[key], value)
        else:
            _apply(current, {key: value})
    return current


def _apply(current: dict, data: dict) -> dict:
    for key, value in data.items():
        if isinstance(value, ArrayUnion):
            current[key] = list(current.get(key) or []) + list(value.values)
        else:
            current[key] = copy.deepcopy(value)
    return current


class FakeQuery:
    def __init__(self, store: Dict[str, dict], filters=()):
        self._store = store
        self._filters = filters

    def where(self, filter=None):  # pylint: disable=redefined-builtin
        assert filter.op_string == "==", "only equality filters are faked"
        return FakeQuery(self._store, self._filters + ((filter.field_path, filter.value),))

    def stream(self):
        for doc_id, data in list(self._store.items()):
            if all(data.get(field) == value for field, value in self._filters):
                yield FakeSnapshotWithId(doc_id, data)


class FakeSnapshotWithId(FakeSnapshot):
    def __init__(self, doc_id: str, data: dict):
        super().__init__(data)
        self.id = doc_id


class FakeCollection(FakeQuery):
    def document(self, doc_id: Optional[str] = None) -> FakeDocRef:
        return FakeDocRef(self._store, doc_id or f"auto-{next(_ids)}")


class FakeBatch:
    def __init__(self):
        self._ops = []

    def set(self, ref: FakeDocRef, data: dict) -> None:
        self._ops.append((ref, data))

    def commit(self) -> None:
        for ref, data in self._ops:
            ref.set(data)


class FakeDb:
    def __init__(self):
        self.collections: Dict[str, Dict[str, dict]] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.collections.setdefault(name, {}))

    def batch(self) -> FakeBatch:
        return FakeBatch()

    def docs(self, name: str) -> Dict[str, dict]:
        return self.collections.get(name, {})


def claim_with_fake_db(db: FakeDb, job_id: str, now: dt.datetime) -> Optional[dict]:
    """Same decision as watch_booking._claim, without a Firestore transaction."""
    job = db.docs("reservationJobs").get(job_id)
    if job is None or not watch_booking.claim_available(job, now):
        return None
    db.collection("reservationJobs").document(job_id).update({"bookingClaimedAt": now})
    return copy.deepcopy(job)


def make_watch_doc(job_id: str, **overrides: Any) -> dict:
    doc = {
        "jobId": job_id,
        "userId": "user-1",
        "venueId": "443",
        "partySize": 2,
        "date": "2026-09-25",
        "rangeStart": "20:00",
        "rangeEnd": "22:00",
        "hour": 20,
        "minute": 0,
        "seatingType": None,
        "watchMode": True,
        "status": "pending",
        "timezone": "America/New_York",
        "bookingFailures": 0,
        "createdAt": dt.datetime(2026, 9, 20, 12, 0, tzinfo=dt.timezone.utc),
    }
    doc.update(overrides)
    return doc
