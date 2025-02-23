"""Inspection frequencies, and the gap that has to be left between two."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.standards.inspection import (
    BRIDGE,
    JOINT_BARS_IN_CWR,
    MONTHLY,
    TURNOUT,
    TWICE_WEEKLY,
    WEEKLY,
    Frequency,
    Weather,
    gap_is_legal,
    is_overdue,
    track_frequency,
)


def test_a_kind_of_track_reads_off_a_chart() -> None:
    assert TrackKind.parse("main").is_main
    assert not TrackKind.parse(" Siding ").is_main
    with pytest.raises(InputError, match="not a kind of track"):
        TrackKind.parse("mainline")


def test_the_upper_classes_are_looked_at_twice_a_week() -> None:
    assert track_frequency(ClassOfTrack.THREE) == WEEKLY
    assert track_frequency(ClassOfTrack.FOUR) == TWICE_WEEKLY
    assert track_frequency(ClassOfTrack.FIVE) == TWICE_WEEKLY


def test_anything_that_is_not_main_track_is_monthly_whatever_its_class() -> None:
    for kind in (TrackKind.SIDING, TrackKind.YARD, TrackKind.INDUSTRY):
        assert track_frequency(ClassOfTrack.FIVE, kind) == MONTHLY
        assert track_frequency(ClassOfTrack.ONE, kind) == MONTHLY


def test_the_longest_a_piece_of_track_goes_unlooked_at() -> None:
    assert WEEKLY.max_gap_days == 7
    assert TWICE_WEEKLY.max_gap_days == 3
    assert MONTHLY.max_gap_days == 30


def test_a_frequency_says_itself_in_the_roadmasters_words() -> None:
    assert WEEKLY.describe() == "once a week, at least 3 days apart"
    assert TWICE_WEEKLY.describe() == "twice a week, at least 1 days apart"
    assert JOINT_BARS_IN_CWR.describe() == "twice a year, at least 90 days apart"
    assert Frequency(3, 90, 10).describe() == "three times a 90 days, at least 10 days apart"


def test_a_frequency_that_allows_no_inspections_is_refused() -> None:
    with pytest.raises(InputError, match="allows no inspections"):
        Frequency(times=1, period_days=7, minimum_gap_days=7)
    with pytest.raises(InputError, match="at least one inspection"):
        Frequency(times=0, period_days=7, minimum_gap_days=1)


def test_two_inspections_too_close_together_do_not_cover_the_cycle() -> None:
    assert not gap_is_legal(WEEKLY, 1)
    assert gap_is_legal(WEEKLY, 3)
    assert gap_is_legal(WEEKLY, 7)
    assert not gap_is_legal(WEEKLY, 8)


def test_a_gap_that_runs_backwards_is_refused() -> None:
    with pytest.raises(InputError, match="cannot come before"):
        gap_is_legal(WEEKLY, -1)


def test_track_is_late_the_day_after_the_cycle_runs_out() -> None:
    assert not is_overdue(WEEKLY, 7)
    assert is_overdue(WEEKLY, 8)
    assert not is_overdue(TWICE_WEEKLY, 3)
    assert is_overdue(TWICE_WEEKLY, 4)
    with pytest.raises(InputError, match="inspected in the future"):
        is_overdue(WEEKLY, -1)


def test_turnouts_and_structures_are_on_their_own_cycles() -> None:
    assert TURNOUT == MONTHLY
    assert BRIDGE.period_days == 365
    assert JOINT_BARS_IN_CWR.times == 2


def test_an_event_reads_off_the_dispatchers_message() -> None:
    assert Weather.parse("flood") == Weather.FLOOD
    assert Weather.parse(" Heavy Rain ") == Weather.HEAVY_RAIN
    with pytest.raises(InputError, match="not an event"):
        Weather.parse("wind")


def test_some_events_stop_the_next_train_and_some_do_not() -> None:
    assert Weather.FLOOD.before_a_train
    assert Weather.EARTHQUAKE.before_a_train
    assert not Weather.HEAT.before_a_train
    assert not Weather.HEAVY_RAIN.before_a_train
