"""Rail sections, wear limits and the flaw testing cycle."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.standards.rail import (
    SECTIONS,
    class_for_wear,
    combined_wear,
    flaw_cycle,
    section,
    wear_limits,
)
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.tonnage import Tonnage


def test_a_section_is_looked_up_by_the_name_on_the_web() -> None:
    assert section("115 RE").pounds_per_yard == 115
    assert section(" 132 re ").name == "132 RE"


def test_a_section_this_railroad_does_not_have_is_refused() -> None:
    with pytest.raises(InputError, match="not a rail section here"):
        section("141 AB")


def test_sections_fall_into_three_weight_bands() -> None:
    assert section("90 ASCE").band == "light"
    assert section("115 RE").band == "medium"
    assert section("136 RE").band == "heavy"
    assert {one.band for one in SECTIONS.values()} == {"light", "medium", "heavy"}


def test_heavier_rail_is_allowed_to_lose_more_head() -> None:
    for one in ALL:
        light = wear_limits(section("90 ASCE"), one)
        heavy = wear_limits(section("136 RE"), one)
        assert heavy.vertical > light.vertical
        assert heavy.combined > light.combined


def test_the_limits_tighten_as_the_class_rises() -> None:
    rows = [wear_limits(section("115 RE"), one) for one in ALL]
    for tighter, looser in zip(rows[1:], rows[:-1], strict=True):
        assert tighter.vertical <= looser.vertical
        assert tighter.gauge_face <= looser.gauge_face


def test_a_sharp_curve_takes_a_sixteenth_off_the_gauge_face() -> None:
    plain = wear_limits(section("115 RE"), ClassOfTrack.THREE)
    curved = wear_limits(section("115 RE"), ClassOfTrack.THREE, Curvature.of(5))
    assert curved.gauge_face == plain.gauge_face - Inches.of(0, 1, 16)
    assert curved.vertical == plain.vertical


def test_a_curve_at_the_threshold_gets_no_allowance() -> None:
    plain = wear_limits(section("115 RE"), ClassOfTrack.THREE)
    assert wear_limits(section("115 RE"), ClassOfTrack.THREE, Curvature.of(4)) == plain


def test_the_combined_figure_is_vertical_plus_half_the_gauge_face() -> None:
    assert combined_wear(Inches.parse("1/4"), Inches.parse("1/2")) == Inches.parse("1/2")
    assert combined_wear(Inches(0), Inches(0)) == Inches(0)


def test_rail_does_not_wear_backwards() -> None:
    with pytest.raises(InputError, match="does not wear backwards"):
        combined_wear(-Inches.of(0, 1, 4), Inches(0))


def test_a_worn_rail_names_the_class_it_still_holds() -> None:
    rail = section("115 RE")
    assert class_for_wear(rail, Inches.parse("1/4"), Inches.parse("1/4")) == ClassOfTrack.FIVE
    assert class_for_wear(rail, Inches.parse("9/16"), Inches.parse("5/8")) == ClassOfTrack.TWO


def test_a_rail_past_every_row_is_done_rather_than_excepted() -> None:
    rail = section("115 RE")
    assert class_for_wear(rail, Inches.parse("1"), Inches.parse("1")) is None


def test_the_combined_figure_pulls_a_class_down_that_both_readings_hold() -> None:
    rail = section("115 RE")
    vertical = Inches.parse("1/2")
    gauge_face = Inches.parse("5/8")
    limits = wear_limits(rail, ClassOfTrack.FOUR)
    assert vertical <= limits.vertical
    assert gauge_face <= limits.gauge_face
    assert combined_wear(vertical, gauge_face) > limits.combined
    assert class_for_wear(rail, vertical, gauge_face) == ClassOfTrack.THREE


def test_the_curve_allowance_can_pull_the_class_down_on_its_own() -> None:
    rail = section("115 RE")
    vertical = Inches.parse("7/16")
    gauge_face = Inches.parse("11/16")
    assert class_for_wear(rail, vertical, gauge_face) == ClassOfTrack.THREE
    assert class_for_wear(rail, vertical, gauge_face, Curvature.of(6)) == ClassOfTrack.TWO


def test_the_lower_classes_have_no_flaw_testing_requirement() -> None:
    for one in (ClassOfTrack.EXCEPTED, ClassOfTrack.ONE, ClassOfTrack.TWO):
        assert not flaw_cycle(one).is_required


def test_the_cycle_shortens_as_the_class_rises() -> None:
    three = flaw_cycle(ClassOfTrack.THREE)
    five = flaw_cycle(ClassOfTrack.FIVE)
    assert three.tonnage == Tonnage.of(40)
    assert three.days == 365
    assert five.tonnage is not None
    assert five.days is not None
    assert five.tonnage < three.tonnage
    assert five.days < three.days
