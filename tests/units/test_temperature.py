"""Rail temperature, and the rule of thumb that stands in for a thermometer."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.units.temperature import (
    Sky,
    Temperature,
    above_neutral,
    hottest_of,
    rail_temperature,
)


def test_a_temperature_reads_off_a_form_with_or_without_the_unit() -> None:
    assert Temperature.parse("95") == Temperature(95)
    assert Temperature.parse("95F") == Temperature(95)
    assert Temperature.parse("-10 degrees") == Temperature(-10)
    assert str(Temperature(95)) == "95F"


@pytest.mark.parametrize("text", ["", "hot", "95.5", "95C", "--10"])
def test_something_that_is_not_a_temperature_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Temperature.parse(text)


def test_a_temperature_this_railroad_never_sees_is_refused() -> None:
    with pytest.raises(InputError, match="not a temperature this railroad sees"):
        Temperature(201)
    with pytest.raises(InputError, match="not a temperature this railroad sees"):
        Temperature(-61)


def test_the_sky_decides_how_far_the_rail_runs_above_the_air() -> None:
    assert Sky.CLEAR.rail_above_air == 30
    assert Sky.PARTLY.rail_above_air == 20
    assert Sky.OVERCAST.rail_above_air == 5


def test_the_sky_reads_off_the_forecast() -> None:
    assert Sky.parse("clear") == Sky.CLEAR
    assert Sky.parse(" OVERCAST ") == Sky.OVERCAST
    with pytest.raises(InputError, match="is not a sky"):
        Sky.parse("raining")


def test_rail_temperature_is_the_air_plus_the_sky() -> None:
    assert rail_temperature(Temperature(90), Sky.CLEAR) == Temperature(120)
    assert rail_temperature(Temperature(90), Sky.OVERCAST) == Temperature(95)


def test_the_difference_from_neutral_is_signed() -> None:
    assert above_neutral(Temperature(120), Temperature(95)) == 25
    assert above_neutral(Temperature(20), Temperature(95)) == -75
    assert Temperature(120).above(Temperature(120)) == 0


def test_warming_a_temperature_can_cool_it() -> None:
    assert Temperature(90).warmer(-15) == Temperature(75)
    with pytest.raises(InputError):
        Temperature(190).warmer(20)


def test_the_hottest_reading_is_the_one_that_governs() -> None:
    got = hottest_of([Temperature(90), Temperature(112), Temperature(75)])
    assert got == Temperature(112)
    with pytest.raises(InputError, match="no temperatures"):
        hottest_of([])


def test_a_list_of_temperatures_sorts_and_compares() -> None:
    assert sorted([Temperature(90), Temperature(-10)]) == [Temperature(-10), Temperature(90)]
    assert Temperature(90) > Temperature(89)
