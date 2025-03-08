"""Crossings with a check letter and bridges with a rating."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.structure import (
    Bridge,
    Crossing,
    Structure,
    Surface,
    WarningDevice,
    check_letter,
    parse_inventory,
)
from spikemaul.units.milepost import Milepost
from spikemaul.units.speed import Speed


def crossing(**changes: object) -> Crossing:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.CROSSING, "244"),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "at": Milepost.parse("22.10"),
        "road": "County Road 14",
        "inventory": f"244160{check_letter(244160)}",
        "surface": Surface.RUBBER,
        "warning": WarningDevice.FLASHERS,
    }
    fields.update(changes)
    return Crossing(**fields)  # type: ignore[arg-type]


def bridge(**changes: object) -> Bridge:
    fields: dict[str, object] = {
        "ident": Ident.named(Kind.BRIDGE, "77"),
        "subdivision": Ident.named(Kind.SUBDIVISION, "PLAINS"),
        "at": Milepost.parse("34.80"),
        "kind": Structure.DECK_GIRDER,
        "spans": 3,
        "length_feet": 186,
        "normal_rating": 60,
        "maximum_rating": 72,
        "built": 1927,
    }
    fields.update(changes)
    return Bridge(**fields)  # type: ignore[arg-type]


def test_the_check_letter_comes_off_the_six_digits() -> None:
    assert check_letter(0) == "A"
    assert check_letter(21) == "Y"
    assert check_letter(22) == "A"
    assert len({check_letter(n) for n in range(22)}) == 22


def test_a_number_that_is_not_six_digits_is_refused() -> None:
    with pytest.raises(InputError, match="not a six digit"):
        check_letter(1_000_000)
    with pytest.raises(InputError, match="not an inventory number"):
        parse_inventory("24416A")


def test_an_inventory_number_whose_letter_is_wrong_is_refused() -> None:
    good = f"244160{check_letter(244160)}"
    assert parse_inventory(good.lower()) == good
    wrong = f"244160{'B' if good[6] != 'B' else 'C'}"
    with pytest.raises(InputError, match="does not check"):
        parse_inventory(wrong)


def test_a_crossing_carries_the_name_of_the_road() -> None:
    with pytest.raises(InputError, match="name of the road"):
        crossing(road="  ")


def test_a_public_timber_crossing_with_no_active_warning_is_refused() -> None:
    with pytest.raises(RuleError, match="no active warning"):
        crossing(surface=Surface.TIMBER, warning=WarningDevice.CROSSBUCKS)
    private = crossing(surface=Surface.TIMBER, warning=WarningDevice.CROSSBUCKS, public=False)
    assert not private.public


def test_a_surface_says_whether_a_gang_can_lift_it_in_a_day() -> None:
    assert Surface.TIMBER.is_removable
    assert not Surface.ASPHALT.is_removable


def test_a_warning_says_whether_it_does_anything_when_a_train_comes() -> None:
    assert WarningDevice.GATES.is_active
    assert WarningDevice.FLASHERS.is_active
    assert not WarningDevice.CROSSBUCKS.is_active


def test_a_crossing_says_itself_in_one_line() -> None:
    line = crossing().describe()
    assert line.startswith("XG-244 PLAINS MP 22.10 County Road 14")
    assert line.endswith("public rubber flashers")


def test_a_bridge_with_no_spans_or_no_length_is_refused() -> None:
    with pytest.raises(InputError, match="at least one span"):
        bridge(spans=0)
    with pytest.raises(InputError, match="at least one span"):
        bridge(length_feet=0)


def test_a_maximum_rating_below_the_normal_one_is_refused() -> None:
    with pytest.raises(InputError, match="not below the normal rating"):
        bridge(normal_rating=72, maximum_rating=60)


def test_a_year_that_is_not_a_year_is_refused() -> None:
    with pytest.raises(InputError, match="not a year a bridge"):
        bridge(built=1780)


def test_the_average_span_is_what_the_inspector_plans_around() -> None:
    assert bridge().average_span_feet == 62


def test_a_load_inside_the_normal_rating_crosses_at_track_speed() -> None:
    assert bridge().restricted_for(60, Speed(40)) == Speed(40)


def test_a_load_over_the_normal_rating_crosses_at_ten() -> None:
    assert bridge().restricted_for(65, Speed(40)) == Speed(10)
    assert bridge().restricted_for(72, Speed(40)) == Speed(10)


def test_a_load_over_the_maximum_does_not_cross_at_any_speed() -> None:
    assert not bridge().carries(80)
    with pytest.raises(RuleError, match="will not take 80"):
        bridge().restricted_for(80, Speed(40))


def test_a_slow_track_speed_still_governs_a_heavy_load() -> None:
    assert bridge().restricted_for(65, Speed(5)) == Speed(5)


def test_the_open_deck_structures_are_named() -> None:
    assert Structure.TIMBER_TRESTLE.is_open_deck
    assert not Structure.BALLAST_DECK.is_open_deck
    assert not Structure.CULVERT.is_open_deck


def test_a_bridge_says_itself_in_one_line() -> None:
    assert bridge().describe() == ("BR-77 PLAINS MP 34.80 deck girder 3 spans 186 ft E 60/72")
