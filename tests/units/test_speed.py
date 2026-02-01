"""Speeds, which are all maxima, and the lowest of them."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.units.speed import RESTRICTED, Speed, minutes_lost, slowest


def test_a_speed_reads_off_a_bulletin_with_or_without_the_unit() -> None:
    assert Speed.parse("25") == Speed(25)
    assert Speed.parse("25 mph") == Speed(25)
    assert Speed.parse(" 40 MPH ") == Speed(40)


def test_restricted_speed_is_spelled_not_numbered() -> None:
    assert Speed.parse("restricted").is_restricted
    assert Speed.parse("RS") == Speed(RESTRICTED)
    assert str(Speed(RESTRICTED)) == "restricted"
    assert str(Speed(25)) == "25 mph"


@pytest.mark.parametrize("text", ["", "fast", "25.5", "-10", "25 kph"])
def test_something_that_is_not_a_speed_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Speed.parse(text)


def test_a_speed_no_train_here_runs_is_refused() -> None:
    with pytest.raises(InputError, match="faster than anything"):
        Speed(120)
    with pytest.raises(InputError, match="not a speed"):
        Speed(-1)


def test_the_lower_of_two_speeds_is_what_the_crew_gets() -> None:
    assert Speed(40).slower_of(Speed(25)) == Speed(25)
    assert Speed(25).slower_of(Speed(40)) == Speed(25)
    assert Speed(25).slower_of(Speed(25)) == Speed(25)


def test_the_slowest_of_a_list_is_the_governing_one() -> None:
    assert slowest([Speed(40), Speed(10), Speed(25)]) == Speed(10)


def test_an_empty_list_of_speeds_is_not_the_same_as_no_restriction() -> None:
    with pytest.raises(InputError, match="not the same as no restriction"):
        slowest([])


def test_running_time_comes_off_the_distance_and_the_speed() -> None:
    assert Speed(60).minutes_over(30) == pytest.approx(30.0)
    assert Speed(25).minutes_over(2.5) == pytest.approx(6.0)


def test_restricted_speed_has_no_running_time() -> None:
    with pytest.raises(InputError, match="does not give a running time"):
        Speed(RESTRICTED).minutes_over(1)


def test_a_restriction_costs_the_difference_in_minutes() -> None:
    assert minutes_lost(Speed(40), Speed(10), 2.0) == pytest.approx(9.0)
    assert minutes_lost(Speed(40), Speed(40), 2.0) == pytest.approx(0.0)


def test_a_speed_above_the_normal_one_is_not_a_restriction() -> None:
    with pytest.raises(InputError, match="not a restriction below"):
        minutes_lost(Speed(25), Speed(40), 1.0)


def test_a_list_of_speeds_sorts_and_compares() -> None:
    assert sorted([Speed(40), Speed(10), Speed(25)]) == [Speed(10), Speed(25), Speed(40)]
    assert Speed(10) < Speed(25)
    assert Speed(25) == Speed(25)
