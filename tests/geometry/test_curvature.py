"""Marking a run up from the curve register before reading it."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.geometry.curvature import curve_at, designated_at, in_spiral, mark_up
from spikemaul.geometry.finding import elevation_findings
from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from tests.support.books import a_curve, a_reading


def run_of(*readings: Reading) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=Ident.named(Kind.SUBDIVISION, "PLAINS"),
        on=date(2025, 5, 6),
        readings=list(readings),
    )


def curves() -> list[Curve]:
    return [a_curve(body="13.10-13.40", elevation="2", spirals=200)]


def test_the_curve_at_a_milepost_takes_in_the_spirals() -> None:
    assert curve_at(curves(), Milepost.parse("13.20")) is not None
    assert curve_at(curves(), Milepost.parse("13.07")) is not None
    assert curve_at(curves(), Milepost.parse("13.00")) is None


def test_the_body_of_the_curve_carries_full_elevation() -> None:
    curve = curves()[0]
    assert designated_at(curve, Milepost.parse("13.20")) == Inches.parse("2")
    assert designated_at(curve, Milepost.parse("13.10")) == Inches.parse("2")
    assert designated_at(curve, Milepost.parse("13.40")) == Inches.parse("2")


def test_the_elevation_is_run_in_across_the_spiral() -> None:
    curve = curves()[0]
    outer = designated_at(curve, Milepost.parse("13.07"))
    inner = designated_at(curve, Milepost.parse("13.09"))
    assert Inches(0) < outer < inner < Inches.parse("2")


def test_a_milepost_outside_the_curve_has_no_designated_elevation() -> None:
    with pytest.raises(ValueError, match="is not in"):
        designated_at(curves()[0], Milepost.parse("13.00"))


def test_a_curve_with_no_spirals_carries_full_elevation_to_its_ends() -> None:
    curve = a_curve(body="13.10-13.40", elevation="2", spirals=0)
    assert designated_at(curve, Milepost.parse("13.10")) == Inches.parse("2")


def test_marking_up_tells_every_station_what_the_chart_says() -> None:
    run = run_of(a_reading("13.00"), a_reading("13.20"), a_reading("13.50"))
    marked = mark_up(run, curves())
    assert [one.on_curve for one in marked.readings] == [False, True, False]
    assert marked.readings[1].designated_elevation == Inches.parse("2")
    assert marked.readings[0].designated_elevation is None


def test_marking_up_replaces_what_the_file_claimed() -> None:
    run = run_of(
        a_reading("13.00", on_curve=True, designated_elevation=Inches.parse("3")),
        a_reading("13.20"),
    )
    marked = mark_up(run, curves())
    assert not marked.readings[0].on_curve
    assert marked.readings[0].designated_elevation is None


def test_an_unmarked_curve_reading_gives_no_elevation_finding_at_all() -> None:
    run = run_of(a_reading("13.20", crosslevel=Inches.parse("2")), a_reading("13.30"))
    assert elevation_findings(run, ClassOfTrack.THREE) == []


def test_a_marked_up_run_finds_the_curve_that_has_lost_its_elevation() -> None:
    run = run_of(
        a_reading("13.20", crosslevel=Inches.parse("1/2")),
        a_reading("13.30", crosslevel=Inches.parse("2")),
    )
    marked = mark_up(run, curves())
    found = elevation_findings(marked, ClassOfTrack.THREE)
    assert [str(one.at) for one in found] == ["13.20"]
    assert found[0].reading == -Inches.parse("1 1/2")


def test_a_station_in_a_spiral_says_it_is_in_one() -> None:
    assert in_spiral(curves(), Milepost.parse("13.07"))
    assert not in_spiral(curves(), Milepost.parse("13.20"))
    assert not in_spiral(curves(), Milepost.parse("13.00"))
