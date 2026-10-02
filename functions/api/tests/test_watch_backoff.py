"""
The bot-block backoff search (watch_backoff.py).

What these protect: probes back away exponentially rather than keep Resy's block topped
up, a ceiling that never clears a block moves up instead of probing it forever, and once
some ceiling clears a block the search narrows towards the shortest one that does.
"""
import datetime as dt

from api import watch_backoff as wb

# 10:00am Eastern on 2026-10-05, well clear of quiet hours on both sides
T0 = dt.datetime(2026, 10, 5, 14, 0, 0, tzinfo=dt.timezone.utc)


def minutes(n: float) -> dt.timedelta:
    return dt.timedelta(minutes=n)


def fail_probes_until(state: dict, end: dt.datetime) -> tuple[dict, list]:
    """Fail every probe the state asks for until `end`. Returns the state and the waits used."""
    waits = []
    while state["nextProbeAt"] <= end:
        state, _ = wb.on_probe_failed(state, state["nextProbeAt"])
        waits.append(state["probeDelay"])
    return state, waits


class TestProbeSpacing:
    def test_first_block_doubles_the_wait_up_to_twenty_minutes(self):
        state = wb.on_block(wb.initial_state(), T0)
        assert state["nextProbeAt"] == T0 + minutes(1)
        state, waits = fail_probes_until(state, T0 + minutes(120))
        assert waits[:7] == [2, 4, 8, 16, 20, 20, 20]

    def test_probe_due_a_moment_after_the_tick_still_goes_on_that_tick(self):
        """Ticks land within a fraction of a second of :50; a probe must not slip a whole minute."""
        state = wb.on_block(wb.initial_state(), T0.replace(microsecond=200_000))
        assert wb.should_probe(state, T0 + minutes(1))
        assert not wb.should_probe(state, T0 + minutes(0.4))

    def test_no_block_means_every_tick_polls(self):
        assert wb.should_probe(wb.initial_state(), T0)


class TestMovingCeiling:
    def test_ceiling_that_never_clears_fails_after_three_hours_and_moves_up(self):
        state = wb.on_block(wb.initial_state(), T0)
        state, _ = fail_probes_until(state, T0 + minutes(179))
        assert state["ceiling"] == 20
        state, waits = fail_probes_until(state, T0 + minutes(200))
        assert state["ceiling"] == 30
        assert state["lo"] == 20
        assert waits[-1] == 30
        assert state["history"][-1]["outcome"] == wb.FAIL

    def test_ceiling_climbs_to_an_hour_and_stops_there(self):
        state = wb.on_block(wb.initial_state(), T0)
        state, _ = fail_probes_until(state, T0 + dt.timedelta(hours=24))
        assert state["ceiling"] == 60
        assert [h["ceiling"] for h in state["history"]][:5] == [20, 30, 40, 50, 60]

    def test_block_that_clears_records_a_pass_and_polling_resumes(self):
        state = wb.on_block(wb.initial_state(), T0)
        state, _ = fail_probes_until(state, T0 + minutes(40))
        state, notes = wb.on_probe_passed(state, T0 + minutes(51))
        assert not wb.is_blocked(state)
        assert state["hi"] == 20
        assert state["history"][-1]["outcome"] == wb.PASS
        assert "block cleared after 51 min under ceiling 20" in notes


class TestSearch:
    def test_bracketed_search_tries_the_midpoint(self):
        assert wb.choose_ceiling(30, 40) == 35

    def test_search_without_a_failed_ceiling_halves_towards_zero(self):
        assert wb.choose_ceiling(None, 20) == 10

    def test_search_stops_within_five_minutes_and_keeps_the_passing_ceiling(self):
        assert wb.choose_ceiling(32, 35) == 35
        assert wb.search_done({"lo": 32, "hi": 35})

    def test_whole_search_converges_on_the_shortest_ceiling_that_clears(self):
        """
        Simulates Resy clearing a block only under ceilings of 33 minutes or more. Every
        episode must end with lo below 33 and hi at or above it, and they must close in.
        """
        threshold = 33
        state = wb.initial_state()
        start = T0
        for _ in range(12):
            state = wb.on_block(state, start)
            end = start + dt.timedelta(hours=20)
            while wb.is_blocked(state):
                at = state["nextProbeAt"]
                assert at < end, "an episode never ended"
                if state["ceiling"] >= threshold and at - state["ceilingSince"] >= minutes(60):
                    state, _ = wb.on_probe_passed(state, at)
                else:
                    state, _ = wb.on_probe_failed(state, at)
            start = start + dt.timedelta(days=1)
            if wb.search_done(state):
                break
        assert wb.search_done(state)
        assert state["lo"] < threshold <= state["hi"]

    def test_failure_at_a_ceiling_that_passed_before_drops_the_pass(self):
        """With noisy results the bracket can invert; it must not lock in a ceiling that failed."""
        state = wb.on_block({**wb.initial_state(), "lo": 30, "hi": 35}, T0)
        assert state["ceiling"] == 35
        notes = []
        while state["nextProbeAt"] <= T0 + minutes(240):
            state, new_notes = wb.on_probe_failed(state, state["nextProbeAt"])
            notes += new_notes
        assert state["hi"] is None
        assert state["lo"] == 35
        assert state["ceiling"] == 45
        assert "ceiling 35 passed before but failed now; dropping it" in notes


class TestQuietHours:
    def test_block_open_across_quiet_hours_is_censored(self):
        # Blocked at 11pm Eastern; the 7:03am tick finds the episode still open.
        start = dt.datetime(2026, 10, 6, 3, 0, tzinfo=dt.timezone.utc)
        state = wb.on_block(wb.initial_state(), start)
        morning = dt.datetime(2026, 10, 6, 11, 3, 50, tzinfo=dt.timezone.utc)
        state, cut = wb.censor_if_cut_by_quiet_hours(state, morning)
        assert cut
        assert not wb.is_blocked(state)
        assert state["lo"] is None and state["hi"] is None
        assert state["history"][-1]["outcome"] == wb.CENSORED

    def test_block_within_one_day_is_not_censored(self):
        state = wb.on_block(wb.initial_state(), T0)
        state, cut = wb.censor_if_cut_by_quiet_hours(state, T0 + dt.timedelta(hours=8))
        assert not cut
        assert wb.is_blocked(state)
