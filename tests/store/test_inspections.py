"""The inspection register, read by date rather than by number."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.store.inspections import Inspections
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.span import Span
from tests.support.books import a_book, a_plain_subdivision, a_subdivision, an_inspection

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def register() -> Inspections:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Inspections(book)


def test_an_inspection_comes_back_the_way_it_went_in() -> None:
    inspections = register()
    inspections.add(an_inspection())
    got = inspections.get(Ident.numbered(Kind.INSPECTION, 2025, 41))
    assert got == an_inspection()


def test_inspections_come_back_oldest_first() -> None:
    inspections = register()
    inspections.add(an_inspection(sequence=44, on=date(2025, 4, 21)))
    inspections.add(an_inspection())
    assert [one.on.day for one in inspections.on(PLAINS)] == [14, 21]


def test_a_scope_can_be_asked_for_on_its_own() -> None:
    inspections = register()
    inspections.add(an_inspection())
    inspections.add(an_inspection(sequence=45, scope=Scope.TURNOUTS, method=Method.WALKING))
    assert len(inspections.on(PLAINS, Scope.TURNOUTS)) == 1
    assert len(inspections.on(PLAINS)) == 2


def test_a_range_of_days_takes_both_ends() -> None:
    inspections = register()
    inspections.add(an_inspection(sequence=41, on=date(2025, 4, 14)))
    inspections.add(an_inspection(sequence=44, on=date(2025, 4, 21)))
    inspections.add(an_inspection(sequence=48, on=date(2025, 5, 2)))
    got = inspections.between(PLAINS, date(2025, 4, 14), date(2025, 4, 21))
    assert [one.ident.sequence for one in got] == [41, 44]


def test_covering_finds_the_ones_that_took_in_any_of_the_stretch() -> None:
    inspections = register()
    inspections.add(an_inspection())
    inspections.add(an_inspection(sequence=46, span="61.40-90.00"))
    got = inspections.covering(PLAINS, Span.parse("60.00-62.00"), Scope.TRACK)
    assert len(got) == 2
    away = inspections.covering(PLAINS, Span.parse("95.00-99.00"), Scope.TRACK)
    assert away == []


def test_the_last_one_covering_a_stretch_has_to_cover_all_of_it() -> None:
    inspections = register()
    inspections.add(an_inspection(sequence=41, on=date(2025, 4, 14)))
    inspections.add(an_inspection(sequence=44, on=date(2025, 4, 21), span="0.00-20.00"))
    found = inspections.last_covering(
        PLAINS, Span.parse("12.00-30.00"), Scope.TRACK, date(2025, 5, 1)
    )
    assert found is not None
    assert found.ident.sequence == 41


def test_an_inspection_after_the_day_asked_about_does_not_count() -> None:
    inspections = register()
    inspections.add(an_inspection(sequence=44, on=date(2025, 4, 21)))
    found = inspections.last_covering(
        PLAINS, Span.parse("12.00-30.00"), Scope.TRACK, date(2025, 4, 20)
    )
    assert found is None


def test_a_stretch_nobody_has_walked_has_no_last_inspection() -> None:
    inspections = register()
    assert (
        inspections.last_covering(PLAINS, Span.parse("12.00-30.00"), Scope.TRACK, date(2025, 5, 1))
        is None
    )


def test_an_inspection_that_is_not_there_is_not_invented() -> None:
    inspections = register()
    with pytest.raises(NotFoundError, match="no inspection"):
        inspections.get(Ident.numbered(Kind.INSPECTION, 2025, 41))
