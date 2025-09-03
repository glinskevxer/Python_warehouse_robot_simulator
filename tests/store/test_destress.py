"""The destress log register."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.cwr.neutral import Destress, neutral_at
from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.destress import DestressLog
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.span import Span
from spikemaul.units.temperature import Temperature
from tests.support.books import a_book, a_subdivision

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
GANG = Ident.named(Kind.PERSON, "DKEHOE")


def register() -> DestressLog:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    return DestressLog(book)


def entry(span: str = "13.00-14.00", on: date = date(2025, 4, 20), neutral: int = 95) -> Destress:
    return Destress(
        subdivision=PLAINS,
        span=Span.parse(span),
        on=on,
        neutral=Temperature(neutral),
        by=GANG,
    )


def test_an_entry_comes_back_the_way_it_went_in() -> None:
    log = register()
    log.add(entry())
    assert log.on(PLAINS) == [entry()]


def test_the_same_stretch_and_day_twice_is_one_entry_written_twice() -> None:
    log = register()
    log.add(entry())
    with pytest.raises(DuplicateError, match="destress entry"):
        log.add(entry(span="13.00-15.00"))


def test_the_same_stretch_on_another_day_is_another_entry() -> None:
    log = register()
    log.add(entry())
    log.add(entry(on=date(2026, 5, 4), neutral=100))
    assert log.count() == 2


def test_the_entries_come_back_oldest_first() -> None:
    log = register()
    log.add(entry(on=date(2026, 5, 4), neutral=100))
    log.add(entry())
    assert [one.on.year for one in log.on(PLAINS)] == [2025, 2026]


def test_the_entries_covering_a_stretch_come_back_newest_first() -> None:
    log = register()
    log.add(entry())
    log.add(entry(on=date(2026, 5, 4), neutral=100))
    got = log.covering(PLAINS, Span.parse("13.20-13.40"), date(2026, 8, 1))
    assert [one.neutral.degrees for one in got] == [100, 95]


def test_the_register_and_the_rule_agree_on_the_neutral_temperature() -> None:
    log = register()
    log.add(entry())
    log.add(entry(on=date(2026, 5, 4), neutral=100))
    entries = log.on(PLAINS)
    assert neutral_at(entries, Span.parse("13.20-13.40"), date(2026, 8, 1)) == Temperature(100)


def test_a_stretch_the_log_does_not_cover_comes_back_empty() -> None:
    log = register()
    log.add(entry())
    assert log.covering(PLAINS, Span.parse("20.00-21.00"), date(2026, 8, 1)) == []


def test_an_entry_can_be_corrected() -> None:
    log = register()
    log.add(entry())
    log.correct(entry(neutral=88))
    assert log.on(PLAINS)[0].neutral == Temperature(88)


def test_correcting_an_entry_nobody_recorded_is_refused() -> None:
    log = register()
    with pytest.raises(NotFoundError, match="no destress entry"):
        log.correct(entry())
