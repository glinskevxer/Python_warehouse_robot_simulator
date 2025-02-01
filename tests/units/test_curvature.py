"""Curves, elevation and the speed the pair of them allow."""

from __future__ import annotations

from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.units.curvature import (
    MAX_UNBALANCE,
    Curvature,
    elevation_for,
    equilibrium_elevation,
    maximum_speed,
    unbalance_at,
)
from spikemaul.units.measure import Inches
from spikemaul.units.speed import Speed


def test_a_curve_reads_off_the_track_chart_in_degrees_and_minutes() -> None:
    assert Curvature.parse("3-30") == Curvature.of(3, 30)
    assert Curvature.parse("3d30") == Curvature.of(3, 30)
    assert Curvature.parse("3 deg 30 min") == Curvature.of(3, 30)
    assert Curvature.parse("3.5") == Curvature.of(3, 30)
    assert Curvature.parse("2") == Curvature.of(2)


def test_a_curvature_finer_than_a_minute_is_refused() -> None:
    with pytest.raises(InputError, match="finer than a minute"):
        Curvature.parse("3.51")


@pytest.mark.parametrize("text", ["", "sharp", "3-90", "-3", "3/4"])
def test_rubbish_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Curvature.parse(text)


def test_a_curve_sharper_than_the_railroad_has_is_refused() -> None:
    with pytest.raises(InputError, match="sharper than any curve"):
        Curvature.of(21)
    with pytest.raises(InputError, match="cannot be less than tangent"):
        Curvature(-1)


def test_tangent_track_is_zero_and_says_so() -> None:
    assert Curvature(0).is_tangent
    assert not Curvature.of(0, 30).is_tangent
    assert str(Curvature.of(3, 30)) == "3 deg 30 min"
    assert str(Curvature(0)) == "0 deg 00 min"


def test_the_degree_is_not_a_radius_and_converts_to_one() -> None:
    assert Curvature.of(1).radius_feet == Decimal("5729.6")
    assert Curvature.of(3, 30).radius_feet == Decimal("1637.0")
    with pytest.raises(InputError, match="tangent track has no radius"):
        assert Curvature(0).radius_feet


def test_equilibrium_elevation_is_the_rule_books_formula() -> None:
    assert equilibrium_elevation(Curvature.of(3), Speed(30)) == Decimal("1.89")
    assert equilibrium_elevation(Curvature.of(2), Speed(40)) == Decimal("2.24")
    assert equilibrium_elevation(Curvature(0), Speed(40)) == Decimal(0)


def test_unbalance_is_what_the_curve_needs_and_does_not_have() -> None:
    got = unbalance_at(Curvature.of(3), Inches.of(1), Speed(30))
    assert got == Decimal("0.89")
    assert unbalance_at(Curvature.of(3), Inches.of(2), Speed(20)) < 0


def test_the_curve_speed_comes_off_the_elevation_and_the_unbalance() -> None:
    got = maximum_speed(Curvature.of(3), Inches.of(1))
    assert got == Speed(43)
    assert maximum_speed(Curvature.of(1), Inches.of(2)) == Speed(84)


def test_the_curve_speed_is_rounded_down_not_to_the_nearest() -> None:
    exact = maximum_speed(Curvature.of(4), Inches.of(0, 1, 2))
    assert exact == Speed(35)


def test_tangent_track_has_no_curve_speed_at_all() -> None:
    assert maximum_speed(Curvature(0), Inches.of(0)) is None


def test_a_curve_with_no_elevation_still_has_a_speed() -> None:
    assert maximum_speed(Curvature.of(6), Inches(0)) == Speed(26)


def test_elevation_past_what_track_carries_is_refused() -> None:
    with pytest.raises(InputError, match="past what track may carry"):
        maximum_speed(Curvature.of(3), Inches.of(7))
    with pytest.raises(InputError, match="not negative"):
        maximum_speed(Curvature.of(3), -Inches.of(1))


def test_unbalance_past_what_freight_runs_is_refused() -> None:
    with pytest.raises(InputError, match="past what freight may run"):
        maximum_speed(Curvature.of(3), Inches.of(1), Inches.of(4))
    assert maximum_speed(Curvature.of(3), Inches.of(1), MAX_UNBALANCE) == Speed(43)


def test_the_elevation_needed_for_a_speed_is_never_negative() -> None:
    assert elevation_for(Curvature.of(4), Speed(40)) == Decimal("1.48")
    assert elevation_for(Curvature.of(1), Speed(20)) == Decimal(0)
