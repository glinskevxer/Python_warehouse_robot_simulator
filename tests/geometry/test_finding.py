"""Findings, which carry the class the reading does meet."""

from __future__ import annotations

from datetime import date

from spikemaul.geometry.finding import (
    alignment_findings,
    crosslevel_findings,
    elevation_findings,
    findings,
    gauge_findings,
    profile_findings,
)
from spikemaul.model.defect import Condition
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.measure import Inches
from tests.support.books import a_reading

CLASS_THREE = ClassOfTrack.THREE


def run_of(*readings: Reading) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=date(2025, 5, 6),
        readings=list(readings),
    )


def test_a_clean_run_has_nothing_on_it() -> None:
    run = run_of(a_reading("12.00"), a_reading("12.01"))
    assert findings(run, CLASS_THREE) == []


def test_a_wide_gauge_is_found_and_carries_the_class_it_meets() -> None:
    run = run_of(a_reading("12.00"), a_reading("12.01", gauge=Inches.parse("57 7/8")))
    found = gauge_findings(run, CLASS_THREE)
    assert len(found) == 1
    assert found[0].condition is Condition.GAUGE
    assert found[0].meets == ClassOfTrack.ONE
    assert found[0].describe() == "MP 12.01 gauge 57 7/8 meets class 1"


def test_a_gauge_that_meets_nothing_says_so() -> None:
    run = run_of(a_reading("12.00", gauge=Inches.parse("58 3/4")), a_reading("12.01"))
    found = gauge_findings(run, CLASS_THREE)
    assert found[0].is_out_of_service
    assert found[0].describe().endswith("meets nothing")


def test_the_same_reading_is_a_finding_on_one_class_and_not_on_another() -> None:
    run = run_of(a_reading("12.00", gauge=Inches.parse("57 5/8")), a_reading("12.01"))
    assert gauge_findings(run, ClassOfTrack.FOUR) != []
    assert gauge_findings(run, ClassOfTrack.THREE) == []


def test_crosslevel_is_judged_on_size_and_not_on_sign() -> None:
    run = run_of(
        a_reading("12.00", crosslevel=Inches.parse("-2")),
        a_reading("12.01", crosslevel=Inches.parse("2")),
    )
    found = crosslevel_findings(run, CLASS_THREE)
    assert [str(one.reading) for one in found] == ["-2", "2"]
    assert {one.meets for one in found} == {ClassOfTrack.TWO}


def test_profile_and_alignment_read_their_own_rows() -> None:
    run = run_of(
        a_reading("12.00", profile=Inches.parse("2 1/2")),
        a_reading("12.01", alignment=Inches.parse("2")),
    )
    assert [one.condition for one in profile_findings(run, CLASS_THREE)] == [Condition.PROFILE]
    assert [one.condition for one in alignment_findings(run, CLASS_THREE)] == [Condition.ALIGNMENT]


def test_alignment_on_a_curve_is_judged_on_the_curve_row() -> None:
    reading = a_reading("12.00", alignment=Inches.parse("11/16"), on_curve=True)
    assert alignment_findings(run_of(reading, a_reading("12.01")), ClassOfTrack.FIVE) != []
    tangent = a_reading("12.00", alignment=Inches.parse("11/16"))
    assert alignment_findings(run_of(tangent, a_reading("12.01")), ClassOfTrack.FIVE) == []


def test_a_curve_reading_with_no_designated_elevation_is_not_judged() -> None:
    reading = a_reading("12.00", on_curve=True, crosslevel=Inches.parse("3"))
    assert elevation_findings(run_of(reading, a_reading("12.01")), CLASS_THREE) == []


def test_the_deviation_from_designated_elevation_is_its_own_finding() -> None:
    reading = a_reading(
        "12.00",
        on_curve=True,
        crosslevel=Inches.parse("3 1/2"),
        designated_elevation=Inches.parse("2"),
    )
    found = elevation_findings(run_of(reading, a_reading("12.01")), CLASS_THREE)
    assert [one.condition for one in found] == [Condition.ELEVATION]
    assert found[0].reading == Inches.parse("1 1/2")


def test_three_channels_out_at_one_station_are_three_findings() -> None:
    reading = a_reading(
        "12.00",
        gauge=Inches.parse("57 7/8"),
        crosslevel=Inches.parse("2"),
        profile=Inches.parse("2 1/2"),
    )
    found = findings(run_of(reading, a_reading("12.01")), CLASS_THREE)
    assert [one.condition.value for one in found] == ["crosslevel", "gauge", "profile"]


def test_findings_come_back_in_milepost_order() -> None:
    run = run_of(
        a_reading("12.00", gauge=Inches.parse("57 7/8")),
        a_reading("12.01"),
        a_reading("12.02", profile=Inches.parse("2 1/2")),
    )
    found = findings(run, CLASS_THREE)
    assert [str(one.at) for one in found] == ["12.00", "12.02"]
