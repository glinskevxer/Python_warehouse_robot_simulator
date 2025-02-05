"""Tonnage, which is what the flaw testing cycle is counted in."""

from __future__ import annotations

from decimal import Decimal

import pytest

from spikemaul.errors import InputError
from spikemaul.units.tonnage import (
    ZERO,
    Tonnage,
    accumulated,
    annual_rate,
    days_to_reach,
)


def test_a_tonnage_reads_off_the_monthly_sheet() -> None:
    assert Tonnage.parse("12.4") == Tonnage.of("12.40")
    assert Tonnage.parse("12.40 MGT") == Tonnage.of("12.4")
    assert Tonnage.parse("7") == Tonnage.of(7)
    assert str(Tonnage.of("12.40")) == "12.40 MGT"


def test_a_figure_finer_than_the_sheet_is_refused() -> None:
    with pytest.raises(InputError, match="finer than the sheets"):
        Tonnage.of("12.401")
    with pytest.raises(InputError, match="not a tonnage"):
        Tonnage.parse("12.401")


@pytest.mark.parametrize("text", ["", "heavy", "-4", "4,000"])
def test_rubbish_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Tonnage.parse(text)


def test_negative_tonnage_is_refused() -> None:
    with pytest.raises(InputError, match="does not run backwards"):
        Tonnage(-1)
    with pytest.raises(InputError, match="do not run backwards"):
        Tonnage.from_gross_tons(-1)


def test_gross_tons_convert_both_ways_at_the_resolution_we_keep() -> None:
    assert Tonnage.from_gross_tons(12_400_000) == Tonnage.of("12.40")
    assert Tonnage.of("12.40").gross_tons == 12_400_000
    assert Tonnage.from_gross_tons(1_004_000) == Tonnage.of("1.00")


def test_tonnage_adds_over_the_months() -> None:
    assert Tonnage.of("1.20") + Tonnage.of("2.30") == Tonnage.of("3.50")
    assert accumulated([Tonnage.of(1), Tonnage.of(2), Tonnage.of("0.50")]) == Tonnage.of("3.50")
    assert accumulated([]) == ZERO


def test_taking_off_more_than_went_over_the_segment_is_refused() -> None:
    assert Tonnage.of(5) - Tonnage.of(2) == Tonnage.of(3)
    with pytest.raises(InputError, match="more tonnage off a segment"):
        Tonnage.of(2) - Tonnage.of(5)


def test_the_yearly_rate_comes_off_a_period() -> None:
    assert annual_rate(Tonnage.of("3.00"), 90) == Decimal("12.17")
    assert annual_rate(Tonnage.of("12.00"), 365) == Decimal("12.00")
    with pytest.raises(InputError, match="at least a day"):
        annual_rate(Tonnage.of(1), 0)


def test_days_to_a_cycle_are_rounded_down() -> None:
    assert days_to_reach(Tonnage.of(40), Tonnage.of(20), Decimal("20.00")) == 365
    assert days_to_reach(Tonnage.of(40), Tonnage.of(30), Decimal("12.00")) == 304


def test_a_segment_already_past_the_cycle_is_due_today() -> None:
    assert days_to_reach(Tonnage.of(40), Tonnage.of(40), Decimal("12.00")) == 0
    assert days_to_reach(Tonnage.of(40), Tonnage.of(41), Decimal("12.00")) == 0


def test_a_segment_with_no_traffic_never_reaches_the_cycle() -> None:
    with pytest.raises(InputError, match="never reaches a cycle"):
        days_to_reach(Tonnage.of(40), Tonnage.of(1), Decimal(0))


def test_tonnages_sort_and_compare() -> None:
    assert sorted([Tonnage.of(3), Tonnage.of(1)]) == [Tonnage.of(1), Tonnage.of(3)]
    assert Tonnage.of("1.50") > Tonnage.of("1.40")
