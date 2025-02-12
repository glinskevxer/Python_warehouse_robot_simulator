"""The geometry table, and the fact that the row read depends on the class."""

from __future__ import annotations

import pytest

from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.standards.geometry import (
    class_for_alignment,
    class_for_crosslevel,
    class_for_elevation_deviation,
    class_for_gauge,
    class_for_profile,
    class_for_warp,
    limits_for,
)
from spikemaul.units.measure import Inches


def test_every_class_has_a_row() -> None:
    assert {one: limits_for(one) for one in ALL}.keys() == set(ALL)


def test_the_limits_tighten_as_the_class_goes_up() -> None:
    rows = [limits_for(one) for one in ALL]
    for tighter, looser in zip(rows[1:], rows[:-1], strict=True):
        assert tighter.gauge_max <= looser.gauge_max
        assert tighter.crosslevel <= looser.crosslevel
        assert tighter.warp <= looser.warp
        assert tighter.profile <= looser.profile


def test_gauge_is_bounded_at_both_ends() -> None:
    row = limits_for(ClassOfTrack.THREE)
    assert row.gauge_holds(Inches.parse("56 1/2"))
    assert row.gauge_holds(Inches.parse("57 3/4"))
    assert not row.gauge_holds(Inches.parse("57 7/8"))
    assert not row.gauge_holds(Inches.parse("55 7/8"))


def test_alignment_on_a_curve_is_tighter_only_at_the_top_class() -> None:
    top = limits_for(ClassOfTrack.FIVE)
    assert top.alignment(on_curve=True) < top.alignment(on_curve=False)
    middle = limits_for(ClassOfTrack.THREE)
    assert middle.alignment(on_curve=True) == middle.alignment(on_curve=False)


def test_a_gauge_reading_names_the_highest_class_it_meets() -> None:
    assert class_for_gauge(Inches.parse("56 1/2")) == ClassOfTrack.FIVE
    assert class_for_gauge(Inches.parse("57 5/8")) == ClassOfTrack.THREE
    assert class_for_gauge(Inches.parse("57 7/8")) == ClassOfTrack.ONE
    assert class_for_gauge(Inches.parse("58 1/4")) == ClassOfTrack.EXCEPTED


def test_a_gauge_reading_that_meets_nothing_is_not_excepted_track() -> None:
    assert class_for_gauge(Inches.parse("58 5/8")) is None
    assert class_for_gauge(Inches.parse("55 1/2")) is None


def test_a_crosslevel_reading_is_judged_on_its_size_not_its_sign() -> None:
    assert class_for_crosslevel(Inches.parse("1")) == ClassOfTrack.FIVE
    assert class_for_crosslevel(Inches.parse("-1")) == ClassOfTrack.FIVE
    assert class_for_crosslevel(Inches.parse("-1 1/2")) == ClassOfTrack.THREE
    assert class_for_crosslevel(Inches.parse("3 1/4")) is None


def test_warp_and_profile_read_their_own_rows() -> None:
    assert class_for_warp(Inches.parse("1 3/4")) == ClassOfTrack.FOUR
    assert class_for_warp(Inches.parse("2 1/8")) == ClassOfTrack.TWO
    assert class_for_profile(Inches.parse("2")) == ClassOfTrack.FOUR
    assert class_for_profile(Inches.parse("2 1/2")) == ClassOfTrack.TWO


def test_alignment_asks_whether_it_is_on_a_curve() -> None:
    reading = Inches.parse("11/16")
    assert class_for_alignment(reading, on_curve=False) == ClassOfTrack.FIVE
    assert class_for_alignment(reading, on_curve=True) == ClassOfTrack.FOUR


def test_a_deviation_from_designated_elevation_reads_its_own_row() -> None:
    assert class_for_elevation_deviation(Inches.parse("3/4")) == ClassOfTrack.FIVE
    assert class_for_elevation_deviation(Inches.parse("1 1/4")) == ClassOfTrack.THREE
    assert class_for_elevation_deviation(Inches.parse("2")) is None


@pytest.mark.parametrize(
    ("reading", "expected"),
    [("1", ClassOfTrack.FIVE), ("1 1/8", ClassOfTrack.FOUR), ("1 1/2", ClassOfTrack.THREE)],
)
def test_the_same_reading_is_inside_one_row_and_outside_another(
    reading: str, expected: ClassOfTrack
) -> None:
    assert class_for_crosslevel(Inches.parse(reading)) == expected
