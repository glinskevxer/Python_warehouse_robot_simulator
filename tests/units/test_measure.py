"""Track measurements, held in sixteenths because the rule book is in fractions."""

from __future__ import annotations

from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.units.measure import (
    STANDARD_GAUGE,
    Inches,
    gauge_deviation,
    widest,
)


def test_a_gauge_reading_is_read_as_a_mixed_number() -> None:
    assert Inches.parse("56 1/2") == Inches.of(56, 1, 2)
    assert Inches.parse("56-1/2") == Inches.of(56, 1, 2)
    assert Inches.parse('57 3/4"') == Inches.of(57, 3, 4)
    assert Inches.parse("57") == Inches.of(57)


def test_a_fraction_on_its_own_is_a_reading() -> None:
    assert Inches.parse("1/4") == Inches.of(0, 1, 4)
    assert Inches.parse("-1/4") == -Inches.of(0, 1, 4)


def test_a_negative_reading_keeps_its_sign() -> None:
    assert Inches.parse("-1/4").sixteenths == -4
    assert Inches.parse("-1 1/4").sixteenths == -20
    assert str(Inches.parse("-1 1/4")) == "-1 1/4"


def test_the_geometry_car_prints_decimals_and_they_are_accepted() -> None:
    assert Inches.parse("56.5") == STANDARD_GAUGE
    assert Inches.from_decimal(Decimal("1.25")) == Inches.of(1, 1, 4)
    assert Inches.parse("-0.75") == -Inches.of(0, 3, 4)


def test_a_reading_finer_than_a_sixteenth_is_refused() -> None:
    with pytest.raises(InputError, match="finer than a sixteenth"):
        Inches.from_decimal(Decimal("1.26"))
    with pytest.raises(InputError, match="finer than a sixteenth"):
        Inches.parse("56.51")


def test_a_denominator_a_sixteenth_does_not_divide_is_refused() -> None:
    with pytest.raises(InputError, match="does not divide"):
        Inches.of(1, 1, 3)
    with pytest.raises(InputError, match="does not divide"):
        Inches.of(1, 1, 0)


def test_the_sign_belongs_on_the_whole_part() -> None:
    with pytest.raises(InputError, match="sign belongs on the whole part"):
        Inches.of(1, -1, 2)


@pytest.mark.parametrize("text", ["", "wide", "1/", "/2", "1 2/", "56 1/2 3/4"])
def test_something_that_is_not_a_measurement_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Inches.parse(text)


def test_a_reading_prints_in_the_lowest_terms_the_bar_is_marked_in() -> None:
    assert str(Inches.of(56, 8, 16)) == "56 1/2"
    assert str(Inches.of(0, 2, 16)) == "1/8"
    assert str(Inches.of(1)) == "1"
    assert str(Inches(0)) == "0"


def test_readings_add_and_subtract_in_sixteenths() -> None:
    assert Inches.of(1, 1, 2) + Inches.of(0, 1, 4) == Inches.of(1, 3, 4)
    assert Inches.of(1, 1, 2) - Inches.of(2) == -Inches.of(0, 1, 2)
    assert -Inches.of(1, 1, 4) == Inches(-20)
    assert abs(Inches(-20)) == Inches(20)


def test_the_value_in_inches_is_exact() -> None:
    assert Inches.of(56, 1, 2).value == Decimal("56.5")
    assert Inches(-4).value == Decimal("-0.25")


def test_gauge_is_measured_as_a_deviation_from_the_bar() -> None:
    assert gauge_deviation(Inches.parse("57 1/4")) == Inches.of(0, 3, 4)
    assert gauge_deviation(Inches.parse("56 1/4")) == -Inches.of(0, 1, 4)
    assert gauge_deviation(STANDARD_GAUGE) == Inches(0)


def test_the_widest_reading_keeps_its_sign() -> None:
    assert widest([Inches.of(0, 1, 2), Inches(-12)]) == Inches(-12)
    assert widest([Inches.of(0, 1, 2), Inches(-8)]) == Inches(8)
    with pytest.raises(InputError, match="no readings"):
        widest([])


def test_readings_sort_by_value_not_by_size() -> None:
    got = sorted([Inches.of(1), Inches(-20), Inches(0)])
    assert got == [Inches(-20), Inches(0), Inches(16)]
