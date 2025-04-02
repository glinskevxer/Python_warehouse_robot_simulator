"""Curve records, their spirals and the speed the elevation buys."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


def curve(**changes: object) -> Curve:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.CURVE, "118"),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "body": Span.parse("13.10-13.40"),
        "curvature": Curvature.of(3),
        "elevation": Inches.parse("2"),
        "hand": Hand.LEFT,
        "entry_spiral_feet": 200,
        "exit_spiral_feet": 200,
    }
    fields.update(changes)
    return Curve(**fields)  # type: ignore[arg-type]


def test_a_curve_of_no_degrees_is_tangent_and_is_not_recorded() -> None:
    with pytest.raises(InputError, match="is tangent track"):
        curve(curvature=Curvature(0))


def test_negative_elevation_is_refused_because_it_is_on_the_outside_rail() -> None:
    with pytest.raises(InputError, match="is not negative"):
        curve(elevation=-Inches.of(1))


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a curve number"):
        curve(ident=Ident.named(Kind.SEGMENT, "014"))
    with pytest.raises(InputError, match="not a subdivision number"):
        curve(subdivision=Ident.named(Kind.CURVE, "118"))


def test_a_negative_spiral_is_refused() -> None:
    with pytest.raises(InputError, match="negative length"):
        curve(entry_spiral_feet=-1)


def test_the_curve_runs_from_the_start_of_one_spiral_to_the_end_of_the_other() -> None:
    subject = curve()
    assert subject.span == Span.parse("13.06-13.44")
    assert subject.holds(Milepost.parse("13.07"))
    assert not subject.holds(Milepost.parse("13.05"))


def test_a_reading_in_a_spiral_is_not_a_reading_in_the_body() -> None:
    subject = curve()
    assert subject.in_spiral(Milepost.parse("13.07"))
    assert not subject.in_spiral(Milepost.parse("13.20"))
    assert not subject.in_spiral(Milepost.parse("13.00"))


def test_the_curve_speed_comes_off_the_elevation_it_carries() -> None:
    assert curve().maximum_speed() == Speed(48)
    assert curve(elevation=Inches.parse("4")).maximum_speed() == Speed(57)
    assert curve().maximum_speed(Inches.of(1)) == Speed(37)


def test_the_balance_speed_is_slower_than_the_maximum() -> None:
    subject = curve()
    assert subject.balance_speed() == Speed(30)
    assert subject.balance_speed() < subject.maximum_speed()


def test_the_elevation_a_speed_would_need_is_the_other_direction() -> None:
    assert curve().elevation_needed(Speed(50)) > curve().elevation.value
    assert curve().elevation_needed(Speed(20)) == 0


def test_a_spiral_has_to_be_long_enough_to_run_the_elevation_in() -> None:
    assert curve().runoff_feet() == 160
    assert curve().spirals_are_long_enough()
    assert not curve(entry_spiral_feet=100).spirals_are_long_enough()
    assert not curve(exit_spiral_feet=100).spirals_are_long_enough()


def test_more_elevation_wants_a_longer_spiral() -> None:
    assert curve(elevation=Inches.parse("4")).runoff_feet() == 320
    assert not curve(elevation=Inches.parse("4")).spirals_are_long_enough()


def test_a_curve_says_itself_in_one_line() -> None:
    assert curve().describe() == "CV-118 PLAINS 13.10 to 13.40 3 deg 00 min left 2 in"
