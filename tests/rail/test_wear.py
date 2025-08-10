"""Rail wear, and the projection the roadmaster plans off."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.model.defect import Condition
from spikemaul.model.side import Hand
from spikemaul.rail.wear import WearReading, tonnage_left, wear_findings, wear_rate
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.tonnage import Tonnage


def reading(**changes: object) -> WearReading:
    fields: dict[str, object] = {
        "at": Milepost.parse("13.20"),
        "hand": Hand.LEFT,
        "rail_section": "115 RE",
        "vertical": Inches.parse("1/4"),
        "gauge_face": Inches.parse("1/4"),
        "measured_on": date(2025, 4, 1),
    }
    fields.update(changes)
    return WearReading(**fields)  # type: ignore[arg-type]


def test_a_section_this_railroad_does_not_have_is_refused() -> None:
    with pytest.raises(InputError, match="not a rail section here"):
        reading(rail_section="141 AB")


def test_rail_does_not_wear_backwards() -> None:
    with pytest.raises(InputError, match="does not wear backwards"):
        reading(vertical=-Inches.of(0, 1, 8))


def test_the_combined_figure_is_the_one_that_condemns() -> None:
    assert reading().combined == Inches.parse("3/8")
    assert reading().class_supported() == ClassOfTrack.FIVE


def test_a_worn_rail_names_the_class_it_holds() -> None:
    worn = reading(vertical=Inches.parse("9/16"), gauge_face=Inches.parse("5/8"))
    assert worn.class_supported() == ClassOfTrack.TWO


def test_a_sharp_curve_pulls_the_class_down_for_the_same_rail() -> None:
    worn = reading(vertical=Inches.parse("7/16"), gauge_face=Inches.parse("11/16"))
    assert worn.class_supported() == ClassOfTrack.THREE
    on_curve = reading(
        vertical=Inches.parse("7/16"),
        gauge_face=Inches.parse("11/16"),
        curve=Curvature.of(6),
    )
    assert on_curve.class_supported() == ClassOfTrack.TWO


def test_a_reading_inside_the_class_is_not_a_finding() -> None:
    assert wear_findings([reading()], ClassOfTrack.THREE) == []


def test_a_reading_below_the_class_is_a_finding_with_what_it_holds() -> None:
    worn = reading(vertical=Inches.parse("9/16"), gauge_face=Inches.parse("5/8"))
    found = wear_findings([worn], ClassOfTrack.FOUR)
    assert [one.condition for one in found] == [Condition.RAIL_WEAR]
    assert found[0].meets == ClassOfTrack.TWO
    assert found[0].reading == Inches.parse("7/8")


def test_rail_past_every_row_is_a_finding_that_meets_nothing() -> None:
    done = reading(vertical=Inches.parse("1"), gauge_face=Inches.parse("1"))
    found = wear_findings([done], ClassOfTrack.ONE)
    assert found[0].is_out_of_service


def test_what_is_left_to_lose_is_never_negative() -> None:
    assert reading().left_to_lose(ClassOfTrack.FOUR) == Inches.parse("3/8")
    done = reading(vertical=Inches.parse("1"), gauge_face=Inches.parse("1"))
    assert done.left_to_lose(ClassOfTrack.FOUR) == Inches(0)


def test_the_wear_rate_is_sixteenths_per_million_gross_tons() -> None:
    first = reading()
    second = reading(
        vertical=Inches.parse("3/8"), gauge_face=Inches.parse("3/8"), measured_on=date(2026, 4, 1)
    )
    assert wear_rate(first, second, Tonnage.of(12)) == Decimal("0.250")


def test_a_rate_off_two_different_rails_is_refused() -> None:
    first = reading()
    other_place = reading(at=Milepost.parse("14.00"), measured_on=date(2026, 4, 1))
    with pytest.raises(InputError, match="same rail at the same place"):
        wear_rate(first, other_place, Tonnage.of(12))
    other_rail = reading(hand=Hand.RIGHT, measured_on=date(2026, 4, 1))
    with pytest.raises(InputError, match="same rail at the same place"):
        wear_rate(first, other_rail, Tonnage.of(12))


def test_a_rate_needs_time_and_tonnage_between_the_readings() -> None:
    first = reading()
    with pytest.raises(InputError, match="not after the first"):
        wear_rate(first, reading(), Tonnage.of(12))
    later = reading(measured_on=date(2026, 4, 1))
    with pytest.raises(InputError, match="needs tonnage"):
        wear_rate(first, later, Tonnage.of(0))


def test_rail_that_reads_less_worn_than_last_time_is_refused() -> None:
    first = reading(vertical=Inches.parse("3/8"))
    second = reading(measured_on=date(2026, 4, 1))
    with pytest.raises(InputError, match="does not grow back"):
        wear_rate(first, second, Tonnage.of(12))


def test_the_tonnage_left_comes_off_the_rate() -> None:
    assert tonnage_left(reading(), ClassOfTrack.FOUR, Decimal("0.25")) == Tonnage.of(24)
    assert tonnage_left(reading(), ClassOfTrack.FOUR, Decimal("0.5")) == Tonnage.of(12)


def test_rail_that_is_not_wearing_has_no_date_to_plan_against() -> None:
    with pytest.raises(InputError, match="no date to plan against"):
        tonnage_left(reading(), ClassOfTrack.FOUR, Decimal(0))


def test_a_reading_says_itself_in_one_line() -> None:
    assert reading().describe() == (
        "MP 13.20 left rail 115 RE vertical 1/4 gauge face 1/4 holds class 5"
    )
