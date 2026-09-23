"""
Refresh the Resy payloads the watch tick tests replay (api/tests/fixtures/resy/).

Calls live Resy the same way the tick does: public API key, no auth token. Only
response bodies are saved, so no credentials can end up in a fixture.

Usage (from functions/):
    python scripts/capture_resy_fixtures.py --venue-id 443 --party-size 2

The script picks one sold-out and one available date from the venue's calendar and
saves the calendar plus a /4/find for each. Signed out, hot venues often show no
available dates at all, so refresh the available fixture from a second venue:
    python scripts/capture_resy_fixtures.py --venue-id 53342 --only available
"""

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position
from api.resy_client.constants import ResyEndpoints  # noqa: E402
from api.watch import build_poll_client  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "api" / "tests" / "fixtures" / "resy"


def _scrub(value):
    """Drop session identifiers Resy echoes back, such as guest_token."""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if k != "guest_token"}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def _save(name: str, body: dict) -> None:
    body = _scrub(body)
    path = FIXTURES / name
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(FIXTURES.parents[3])}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venue-id", required=True)
    parser.add_argument("--party-size", type=int, default=2)
    parser.add_argument("--only", choices=["available", "sold-out"],
                        help="refresh only this find fixture (venues rarely have both kinds signed out)")
    args = parser.parse_args()

    client = build_poll_client().client
    today = dt.date.today()
    calendar = client.get(ResyEndpoints.CALENDAR.value, params={
        "venue_id": args.venue_id,
        "num_seats": args.party_size,
        "start_date": today.isoformat(),
        "end_date": (today + dt.timedelta(days=30)).isoformat(),
    }).json()
    if not args.only:
        _save("calendar.json", calendar)

    by_status = {}
    for entry in calendar.get("scheduled", []):
        by_status.setdefault((entry.get("inventory") or {}).get("reservation"), entry["date"])

    for status, name in (("available", "find_available.json"), ("sold-out", "find_sold_out.json")):
        if args.only and status != args.only:
            continue
        day = by_status.get(status)
        if not day:
            print(f"no {status} date in the calendar; {name} not refreshed")
            continue
        body = client.post_json(ResyEndpoints.FIND.value, body={
            "lat": 0, "long": 0, "day": day, "party_size": args.party_size, "venue_id": int(args.venue_id),
        }).json()
        _save(name, body)


if __name__ == "__main__":
    main()
