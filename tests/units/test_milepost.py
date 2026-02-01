"""Milepost arithmetic, which every other position in the book is built on."""

from __future__ import annotations

from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.units.milepost import FEET_PER_MILE, Milepost


def test_a_milepost_reads_back_the_way_the_chart_writes_it() -> None:
    assert str(Milepost.parse("43.2")) == "43.20"
    assert str(Milepost.parse("43.20")) == "43.20"
    assert str(Milepost.parse("MP 43.20")) == "43.20"
    assert str(Milepost.parse("mp43")) == "43.00"


def test_the_station_form_is_read_and_written() -> None:
    assert Milepost.parse("43+1056") == Milepost.of(43, 20)
    assert Milepost.of(43, 20).station() == "43+1056"
    assert Milepost.of(12, 0).station() == "12+0"


def test_a_station_that_is_not_a_whole_hundredth_is_refused() -> None:
    with pytest.raises(InputError, match="not a whole hundredth"):
        Milepost.parse("43+100")


def test_a_station_past_the_next_post_is_refused() -> None:
    with pytest.raises(InputError, match="past the next milepost"):
        Milepost.parse("43+5280")


def test_a_third_decimal_place_is_refused_rather_than_rounded() -> None:
    with pytest.raises(InputError, match="not a milepost"):
        Milepost.parse("43.205")


@pytest.mark.parametrize("text", ["", "   ", "43.9x", "MP", "-3.20", "43,20", "43.2.1"])
def test_rubbish_in_the_field_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Milepost.parse(text)


def test_the_whole_post_and_the_part_past_it_are_separate() -> None:
    post = Milepost.parse("61.07")
    assert post.whole == 61
    assert post.into_mile == 7
    assert post.miles == Decimal("61.07")


def test_hundredths_out_of_range_are_refused() -> None:
    with pytest.raises(InputError, match="not a hundredth"):
        Milepost.of(43, 100)
    with pytest.raises(InputError, match="not a hundredth"):
        Milepost.of(43, -1)


def test_a_negative_position_is_refused() -> None:
    with pytest.raises(InputError, match="before the start"):
        Milepost(-1)


def test_miles_can_be_given_as_a_decimal_but_not_finer_than_a_hundredth() -> None:
    assert Milepost.from_miles("43.20") == Milepost.of(43, 20)
    assert Milepost.from_miles(Decimal("7")) == Milepost.of(7)
    with pytest.raises(InputError, match="finer than a hundredth"):
        Milepost.from_miles("43.205")
    with pytest.raises(InputError, match="not a number of miles"):
        Milepost.from_miles("north end")


def test_the_nominal_distance_is_signed_and_in_feet() -> None:
    here = Milepost.of(43, 20)
    ahead = Milepost.of(44, 20)
    assert here.nominal_feet_to(ahead) == FEET_PER_MILE
    assert ahead.nominal_feet_to(here) == -FEET_PER_MILE
    assert here.nominal_feet_to(here) == 0
    assert Milepost.of(1).nominal_feet_to(Milepost.of(1, 1)) == 53


def test_advancing_moves_by_hundredths_and_by_feet() -> None:
    post = Milepost.of(10, 50)
    assert post.advanced(25) == Milepost.of(10, 75)
    assert post.advanced(-50) == Milepost.of(10)
    assert post.advanced_feet(FEET_PER_MILE) == Milepost.of(11, 50)
    assert post.advanced_feet(-528) == Milepost.of(10, 40)


def test_advancing_off_the_start_of_the_line_is_refused() -> None:
    with pytest.raises(InputError, match="runs off the start"):
        Milepost.of(0, 10).advanced(-11)


def test_a_list_of_mileposts_sorts_by_position() -> None:
    posts = [Milepost.of(44), Milepost.of(43, 20), Milepost.of(43, 2)]
    assert [str(post) for post in sorted(posts)] == ["43.02", "43.20", "44.00"]


def test_a_milepost_is_hashable_so_it_can_key_a_map() -> None:
    counts = {Milepost.of(43, 20): 2}
    counts[Milepost.parse("43.20")] += 1
    assert counts == {Milepost.of(43, 20): 3}
