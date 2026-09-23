"""
Caps exist because every watched (venue, party size) pair costs Resy requests every
minute from our IPs. Joining a pair someone already watches costs nothing extra.
"""
from api.constants import WATCH_MAX_PER_USER, WATCH_MAX_TARGETS
from api.watch_limits import limit_error


def watch(user: str, venue: str, party: int = 2) -> dict:
    return {"userId": user, "venueId": venue, "partySize": party}


def test_user_under_cap_is_allowed():
    assert limit_error([watch("u1", "1")], "u1", "2", 2) is None


def test_user_cap_blocks_the_next_watch():
    existing = [watch("u1", str(v)) for v in range(WATCH_MAX_PER_USER)]
    assert "at most" in limit_error(existing, "u1", "999", 2)


def test_other_users_watches_do_not_count_toward_mine():
    existing = [watch("u2", str(v)) for v in range(WATCH_MAX_PER_USER)]
    assert limit_error(existing, "u1", "999", 2) is None


def test_global_target_cap_blocks_a_new_target():
    existing = [watch(f"u{v}", str(v)) for v in range(WATCH_MAX_TARGETS)]
    assert "capacity" in limit_error(existing, "new-user", "999", 2)


def test_joining_an_existing_target_at_capacity_is_allowed():
    existing = [watch(f"u{v}", str(v)) for v in range(WATCH_MAX_TARGETS)]
    assert limit_error(existing, "new-user", "0", 2) is None


def test_party_size_makes_a_different_target():
    """Resy inventory differs by party size, so (venue, 2) and (venue, 4) are polled separately."""
    existing = [watch(f"u{v}", str(v)) for v in range(WATCH_MAX_TARGETS)]
    assert "capacity" in limit_error(existing, "new-user", "0", 4)
