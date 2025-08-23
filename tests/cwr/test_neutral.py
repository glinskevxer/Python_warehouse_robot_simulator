"""The destress log, which is the only record of neutral temperature."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.cwr.neutral import (
    DESIGN_NEUTRAL,
    Destress,
    days_since_destress,
    last_destress,
    neutral_at,
    out_of_specification,
)
from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.span import Span
from spikemaul.units.temperature import Temperature

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
GANG = Ident.named(Kind.PERSON, "DKEHOE")


def entry(
    span: str = "13.00-14.00",
    on: date = date(2025, 4, 20),
    neutral: int = 95,
    method: str = "heater",
) -> Destress:
    return Destress(
        subdivision=PLAINS,
        span=Span.parse(span),
        on=on,
        neutral=Temperature(neutral),
        by=GANG,
        method=method,
    )


def test_a_record_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(InputError, match="not a subdivision number"):
        Destress(GANG, Span.parse("13.00-14.00"), date(2025, 4, 20), Temperature(95), GANG)
    with pytest.raises(InputError, match="is not a person"):
        Destress(PLAINS, Span.parse("13.00-14.00"), date(2025, 4, 20), Temperature(95), PLAINS)


def test_an_entry_says_how_it_was_done() -> None:
    with pytest.raises(InputError, match="says how it was done"):
        entry(method="  ")


def test_a_stretch_with_no_entry_has_no_neutral_temperature() -> None:
    assert neutral_at([], Span.parse("13.00-14.00"), date(2025, 8, 1)) is None
    assert last_destress([], Span.parse("13.00-14.00"), date(2025, 8, 1)) is None
    assert days_since_destress([], Span.parse("13.00-14.00"), date(2025, 8, 1)) is None


def test_nothing_is_not_the_design_temperature() -> None:
    got = neutral_at([], Span.parse("13.00-14.00"), date(2025, 8, 1))
    assert got is None
    assert Temperature(95) == DESIGN_NEUTRAL


def test_the_latest_entry_covering_the_stretch_governs() -> None:
    log = [entry(), entry(on=date(2026, 5, 4), neutral=100)]
    assert neutral_at(log, Span.parse("13.20-13.40"), date(2026, 8, 1)) == Temperature(100)
    assert neutral_at(log, Span.parse("13.20-13.40"), date(2026, 1, 1)) == Temperature(95)


def test_an_entry_that_does_not_take_in_the_whole_stretch_does_not_count() -> None:
    log = [entry(span="13.00-13.50")]
    assert neutral_at(log, Span.parse("13.00-14.00"), date(2025, 8, 1)) is None
    assert neutral_at(log, Span.parse("13.10-13.40"), date(2025, 8, 1)) == Temperature(95)


def test_days_since_the_last_destress_are_counted_from_the_entry() -> None:
    log = [entry(on=date(2025, 4, 20))]
    assert days_since_destress(log, Span.parse("13.20-13.40"), date(2025, 5, 20)) == 30


def test_an_entry_outside_the_range_we_lay_to_says_so() -> None:
    assert entry(neutral=90).in_specification
    assert entry(neutral=105).in_specification
    assert not entry(neutral=106).in_specification
    assert not entry(neutral=80).in_specification


def test_the_entries_out_of_specification_can_be_asked_for() -> None:
    log = [entry(), entry(on=date(2025, 6, 1), neutral=78)]
    assert [one.neutral.degrees for one in out_of_specification(log)] == [78]


def test_an_entry_says_itself_in_one_line() -> None:
    assert entry().describe() == "2025-04-20 PLAINS 13.00 to 14.00 heater to 95F"
    assert entry(neutral=78).describe().endswith("out of specification")
