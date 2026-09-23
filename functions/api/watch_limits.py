"""
Caps on cancellation watches. Every active (venueId, partySize) pair costs Resy
requests every minute from our IPs, so the number of pairs is capped globally and
the number of watches is capped per user.
"""

from typing import List, Optional

from google.cloud.firestore_v1.base_query import FieldFilter

from .constants import WATCH_MAX_PER_USER, WATCH_MAX_TARGETS


def target_id(venue_id, party_size) -> str:
    return f"{venue_id}_{int(party_size)}"


def limit_error(active_watches: List[dict], user_id: str, venue_id, party_size) -> Optional[str]:
    """
    Return a user-facing error if a new watch would break a cap, else None.
    active_watches are the pending watchMode jobs across all users.
    """
    user_count = sum(1 for w in active_watches if w.get("userId") == user_id)
    if user_count >= WATCH_MAX_PER_USER:
        return f"You can have at most {WATCH_MAX_PER_USER} active cancellation watches."

    targets = {target_id(w["venueId"], w["partySize"]) for w in active_watches}
    # Joining a target someone already watches adds no Resy requests, so it is always allowed.
    if target_id(venue_id, party_size) not in targets and len(targets) >= WATCH_MAX_TARGETS:
        return "Cancellation watching is at capacity right now. Try again later."
    return None


def load_active_watches(db) -> List[dict]:
    query = (
        db.collection("reservationJobs")
        .where(filter=FieldFilter("watchMode", "==", True))
        .where(filter=FieldFilter("status", "==", "pending"))
    )
    return [doc.to_dict() for doc in query.stream()]
