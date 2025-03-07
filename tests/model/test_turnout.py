"""Turnouts, whose diverging speed does not come off the class of track."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.turnout import (
    FROG_FLANGEWAY_MIN,
    POINT_GAP_LIMIT,
    FrogKind,
    Hand,
    Throw,
    Turnout,
)
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.speed import Speed


def turnout(**changes: object) -> Turnout:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.TURNOUT, "31"),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "point_of_switch": Milepost.parse("18.60"),
        "size": 10,
        "hand": Hand.RIGHT,
        "frog": FrogKind.RIGID,
        "throw": Throw.HAND,
    }
    fields.update(changes)
    return Turnout(**fields)  # type: ignore[arg-type]


def test_a_size_this_railroad_does_not_stock_is_refused() -> None:
    with pytest.raises(InputError, match="not a turnout size here"):
        turnout(size=12)


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a turnout number"):
        turnout(ident=Ident.named(Kind.CURVE, "118"))
    with pytest.raises(InputError, match="not a subdivision number"):
        turnout(subdivision=Ident.named(Kind.TURNOUT, "31"))


def test_a_spring_switch_is_not_built_with_a_moveable_point_frog() -> None:
    with pytest.raises(InputError, match="not built with a moveable point frog"):
        turnout(throw=Throw.SPRING, frog=FrogKind.MOVEABLE)


def test_the_diverging_speed_comes_off_the_frog_number() -> None:
    assert turnout(size=8).diverging_speed == Speed(15)
    assert turnout(size=10).diverging_speed == Speed(20)
    assert turnout(size=20).diverging_speed == Speed(40)


def test_the_diverging_speed_holds_even_where_the_class_allows_more() -> None:
    assert turnout(size=8).speed_through(diverging=True, class_speed=Speed(60)) == Speed(15)
    assert turnout(size=8).speed_through(diverging=False, class_speed=Speed(60)) == Speed(60)


def test_a_slow_class_still_governs_the_diverging_route() -> None:
    assert turnout(size=20).speed_through(diverging=True, class_speed=Speed(25)) == Speed(25)


def test_a_point_standing_off_its_stock_rail_is_a_defect_at_a_quarter_inch() -> None:
    subject = turnout()
    assert not subject.point_gap_is_a_defect(Inches.parse("3/16"))
    assert subject.point_gap_is_a_defect(POINT_GAP_LIMIT)
    assert subject.point_gap_is_a_defect(Inches.parse("1/2"))


def test_a_negative_point_gap_is_refused() -> None:
    with pytest.raises(InputError, match="not negative"):
        turnout().point_gap_is_a_defect(-Inches.of(0, 1, 8))


def test_a_worn_frog_flangeway_and_guard_check_are_their_own_limits() -> None:
    subject = turnout()
    assert subject.flangeway_is_a_defect(Inches.parse("1 7/16"))
    assert not subject.flangeway_is_a_defect(FROG_FLANGEWAY_MIN)
    assert subject.guard_check_is_a_defect(Inches.parse("54"))
    assert not subject.guard_check_is_a_defect(Inches.parse("54 1/4"))


def test_the_frogs_that_wear_by_battering_are_named() -> None:
    assert FrogKind.RIGID.wears_by_batter
    assert FrogKind.SELF_GUARDED.wears_by_batter
    assert not FrogKind.SPRING.wears_by_batter
    assert not FrogKind.MOVEABLE.wears_by_batter


def test_a_turnout_says_itself_in_one_line() -> None:
    assert turnout(leads_to="Bartels elevator").describe() == (
        "TO-31 PLAINS MP 18.60 no 10 right hand rigid frog hand throw to Bartels elevator"
    )
    assert turnout().describe().endswith("hand throw")
