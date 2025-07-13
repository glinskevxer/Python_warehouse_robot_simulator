"""What class the track holds, and the walk down to it."""

from __future__ import annotations

from datetime import date

from spikemaul.geometry.assessment import assess, downgrade_path, supported_class
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.remedial import Remedy
from spikemaul.units.measure import Inches
from tests.support.books import a_reading


def run_of(*readings: Reading) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=date(2025, 5, 6),
        readings=list(readings),
    )


def clean() -> Run:
    return run_of(a_reading("12.00"), a_reading("12.01"), a_reading("12.02"))


def with_wide_gauge(gauge: str = "57 7/8") -> Run:
    return run_of(
        a_reading("12.00"),
        a_reading("12.01", gauge=Inches.parse(gauge)),
        a_reading("12.02"),
    )


def test_a_clean_run_meets_the_class_it_is_held_to() -> None:
    got = assess(clean(), ClassOfTrack.THREE)
    assert got.is_clear
    assert got.action.remedy is Remedy.NONE
    assert got.worst is None
    assert got.describe() == "12.00 to 12.02 meets class 3, 0 exceptions"


def test_the_supported_class_is_the_lowest_any_reading_holds() -> None:
    assert supported_class(clean()) == ClassOfTrack.FIVE
    assert supported_class(with_wide_gauge()) == ClassOfTrack.ONE


def test_a_run_with_a_reading_that_meets_nothing_supports_nothing() -> None:
    assert supported_class(with_wide_gauge("58 3/4")) is None


def test_a_run_held_too_high_is_held_at_what_it_supports() -> None:
    got = assess(with_wide_gauge(), ClassOfTrack.THREE)
    assert not got.is_clear
    assert got.supports == ClassOfTrack.ONE
    assert got.action.remedy is Remedy.RESTRICT
    assert got.action.hold_at == ClassOfTrack.ONE
    assert got.describe().endswith("supports class 1")


def test_a_run_that_supports_nothing_takes_the_track_out() -> None:
    got = assess(with_wide_gauge("58 3/4"), ClassOfTrack.THREE)
    assert got.action.takes_track_out


def test_the_walk_settles_on_the_first_step() -> None:
    run = with_wide_gauge()
    first = assess(run, ClassOfTrack.THREE)
    assert first.supports is not None
    again = assess(run, first.supports)
    assert again.is_clear
    assert again.supports == first.supports


def test_the_same_run_reads_differently_on_two_classes() -> None:
    run = with_wide_gauge("57 5/8")
    assert not assess(run, ClassOfTrack.FOUR).is_clear
    assert assess(run, ClassOfTrack.THREE).is_clear


def test_the_worst_finding_is_the_one_holding_the_class_down() -> None:
    run = run_of(
        a_reading("12.00", profile=Inches.parse("2 1/2")),
        a_reading("12.01", gauge=Inches.parse("57 7/8")),
        a_reading("12.02"),
    )
    got = assess(run, ClassOfTrack.THREE)
    worst = got.worst
    assert worst is not None
    assert str(worst.at) == "12.01"
    assert worst.meets == ClassOfTrack.ONE


def test_warp_is_part_of_the_assessment_and_not_only_the_channels() -> None:
    run = run_of(
        a_reading("12.00", crosslevel=Inches.parse("-1")),
        a_reading("12.01", crosslevel=Inches.parse("1")),
        a_reading("12.02", crosslevel=Inches.parse("-1")),
    )
    got = assess(run, ClassOfTrack.FIVE)
    assert [one.condition.value for one in got.exceptions] == ["warp", "warp"]
    assert got.supports == ClassOfTrack.THREE


def test_a_track_that_meets_its_class_has_a_path_of_one() -> None:
    assert downgrade_path(clean(), ClassOfTrack.THREE) == [ClassOfTrack.THREE]


def test_the_path_runs_from_the_class_held_down_to_the_one_supported() -> None:
    got = downgrade_path(with_wide_gauge(), ClassOfTrack.FOUR)
    assert got == [
        ClassOfTrack.FOUR,
        ClassOfTrack.THREE,
        ClassOfTrack.TWO,
        ClassOfTrack.ONE,
    ]


def test_a_path_that_reaches_excepted_and_still_fails_is_the_clue() -> None:
    got = downgrade_path(with_wide_gauge("58 3/4"), ClassOfTrack.THREE)
    assert got[-1] == ClassOfTrack.EXCEPTED
    assert not assess(with_wide_gauge("58 3/4"), ClassOfTrack.EXCEPTED).is_clear
