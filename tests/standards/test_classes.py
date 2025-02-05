"""Classes of track, which are a statement of limits rather than of condition."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.standards.classes import (
    ALL,
    ClassOfTrack,
    Traffic,
    class_for_speed,
    classes_at_or_below,
    speed_limit,
)
from spikemaul.units.speed import Speed


def test_a_class_reads_off_a_chart_however_it_is_written() -> None:
    assert ClassOfTrack.parse("3") == ClassOfTrack.THREE
    assert ClassOfTrack.parse("class 3") == ClassOfTrack.THREE
    assert ClassOfTrack.parse("Class 1") == ClassOfTrack.ONE
    assert ClassOfTrack.parse("excepted") == ClassOfTrack.EXCEPTED
    assert ClassOfTrack.parse("X") == ClassOfTrack.EXCEPTED


@pytest.mark.parametrize("text", ["", "6", "0", "class", "main"])
def test_something_that_is_not_a_class_is_refused(text: str) -> None:
    with pytest.raises(InputError, match="not a class of track"):
        ClassOfTrack.parse(text)


def test_a_class_prints_the_way_the_bulletin_writes_it() -> None:
    assert str(ClassOfTrack.THREE) == "class 3"
    assert str(ClassOfTrack.EXCEPTED) == "excepted"


def test_the_freight_speeds_are_the_ones_out_of_the_rule_book() -> None:
    assert [speed_limit(one).mph for one in ALL] == [10, 10, 25, 40, 60, 80]


def test_passenger_speed_is_higher_on_every_class_that_carries_it() -> None:
    for one in ALL:
        if one.carries(Traffic.PASSENGER):
            assert speed_limit(one, Traffic.PASSENGER) > speed_limit(one)


def test_excepted_track_carries_no_passengers_at_any_speed() -> None:
    assert not ClassOfTrack.EXCEPTED.carries(Traffic.PASSENGER)
    with pytest.raises(InputError, match="does not run on excepted"):
        speed_limit(ClassOfTrack.EXCEPTED, Traffic.PASSENGER)


def test_traffic_reads_off_a_form() -> None:
    assert Traffic.parse("freight") == Traffic.FREIGHT
    assert Traffic.parse(" Passenger ") == Traffic.PASSENGER
    with pytest.raises(InputError, match="not freight or passenger"):
        Traffic.parse("empties")


def test_the_class_to_hold_to_is_the_lowest_one_that_allows_the_speed() -> None:
    assert class_for_speed(Speed(10)) == ClassOfTrack.EXCEPTED
    assert class_for_speed(Speed(11)) == ClassOfTrack.TWO
    assert class_for_speed(Speed(25)) == ClassOfTrack.TWO
    assert class_for_speed(Speed(41)) == ClassOfTrack.FOUR


def test_a_speed_no_class_carries_is_refused() -> None:
    with pytest.raises(InputError, match="no class of track carries"):
        class_for_speed(Speed(90))
    assert class_for_speed(Speed(90), Traffic.PASSENGER) == ClassOfTrack.FIVE


def test_classes_sort_with_excepted_at_the_bottom() -> None:
    assert ClassOfTrack.EXCEPTED < ClassOfTrack.ONE < ClassOfTrack.FIVE
    assert ClassOfTrack.FIVE >= ClassOfTrack.FIVE
    assert ClassOfTrack.THREE > ClassOfTrack.TWO
    assert ClassOfTrack.TWO <= ClassOfTrack.THREE
    assert sorted([ClassOfTrack.FOUR, ClassOfTrack.EXCEPTED])[0].is_excepted


def test_the_classes_a_segment_can_drop_to_come_back_highest_first() -> None:
    got = classes_at_or_below(ClassOfTrack.THREE)
    assert got == (
        ClassOfTrack.THREE,
        ClassOfTrack.TWO,
        ClassOfTrack.ONE,
        ClassOfTrack.EXCEPTED,
    )
    assert classes_at_or_below(ClassOfTrack.EXCEPTED) == (ClassOfTrack.EXCEPTED,)


def test_the_rank_is_what_sorting_and_the_tables_key_on() -> None:
    assert ClassOfTrack.EXCEPTED.rank == 0
    assert ClassOfTrack.FIVE.rank == 5
