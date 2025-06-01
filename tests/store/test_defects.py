"""The defect register, asked what is still open more than anything else."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import NotFoundError
from spikemaul.model.defect import Condition
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.defects import Defects
from spikemaul.store.inspections import Inspections
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.span import Span
from tests.support.books import (
    a_book,
    a_defect,
    a_plain_subdivision,
    a_subdivision,
    an_inspection,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def register() -> Defects:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    Inspections(book).add(an_inspection(sequence=41, on=date(2025, 5, 6)))
    return Defects(book)


def test_a_card_comes_back_the_way_it_went_in() -> None:
    defects = register()
    defects.add(a_defect())
    assert defects.get(Ident.numbered(Kind.DEFECT, 2025, 142)) == a_defect()


def test_a_card_that_meets_no_class_keeps_its_null() -> None:
    defects = register()
    defects.add(a_defect(meets=None, condition=Condition.RAIL_BREAK, reading="broken base"))
    got = defects.get(Ident.numbered(Kind.DEFECT, 2025, 142))
    assert got.meets is None


def test_open_is_having_no_repair_date_and_nothing_else() -> None:
    defects = register()
    defects.add(a_defect())
    defects.add(a_defect(sequence=143, at="14.00", repaired_on=date(2025, 5, 20)))
    assert [one.ident.sequence for one in defects.open_on(PLAINS)] == [142]


def test_open_cards_come_back_in_milepost_order() -> None:
    defects = register()
    defects.add(a_defect(sequence=150, at="20.00"))
    defects.add(a_defect())
    assert [str(one.at) for one in defects.open_on(PLAINS)] == ["13.22", "20.00"]


def test_open_cards_can_be_asked_for_inside_a_stretch() -> None:
    defects = register()
    defects.add(a_defect())
    defects.add(a_defect(sequence=150, at="20.00"))
    got = defects.open_within(PLAINS, Span.parse("13.00-14.00"))
    assert [one.ident.sequence for one in got] == [142]


def test_the_cards_that_stop_trains_can_be_asked_for_on_their_own() -> None:
    defects = register()
    defects.add(a_defect())
    defects.add(
        a_defect(
            sequence=143,
            at="14.00",
            meets=None,
            condition=Condition.RAIL_BREAK,
            reading="broken base",
        )
    )
    assert [one.ident.sequence for one in defects.out_of_service(PLAINS)] == [143]


def test_cards_can_be_asked_for_by_the_days_they_were_raised() -> None:
    defects = register()
    defects.add(a_defect())
    defects.add(a_defect(sequence=200, at="15.00", found_on=date(2025, 7, 1)))
    got = defects.raised_between(date(2025, 5, 1), date(2025, 6, 1))
    assert [one.ident.sequence for one in got] == [142]


def test_cards_can_be_asked_for_by_the_inspection_they_came_off() -> None:
    defects = register()
    defects.add(a_defect(inspection=41))
    defects.add(a_defect(sequence=143, at="14.00"))
    got = defects.from_inspection(Ident.numbered(Kind.INSPECTION, 2025, 41))
    assert [one.ident.sequence for one in got] == [142]


def test_repairing_a_card_is_writing_it_back_over_itself() -> None:
    defects = register()
    defects.add(a_defect())
    card = defects.get(Ident.numbered(Kind.DEFECT, 2025, 142))
    defects.update(card.repaired(date(2025, 5, 20)))
    assert defects.open_on(PLAINS) == []
    assert defects.count() == 1


def test_the_next_number_follows_the_highest_one_that_year() -> None:
    defects = register()
    assert defects.next_number(2025) == Ident.numbered(Kind.DEFECT, 2025, 1)
    defects.add(a_defect())
    defects.add(a_defect(sequence=9, at="14.00"))
    assert defects.next_number(2025) == Ident.numbered(Kind.DEFECT, 2025, 143)
    assert defects.next_number(2026) == Ident.numbered(Kind.DEFECT, 2026, 1)


def test_a_card_that_is_not_there_is_not_invented() -> None:
    defects = register()
    with pytest.raises(NotFoundError, match="no defect"):
        defects.get(Ident.numbered(Kind.DEFECT, 2025, 142))


def test_a_card_keeps_the_class_it_meets_through_the_book() -> None:
    defects = register()
    defects.add(a_defect(meets=ClassOfTrack.EXCEPTED))
    got = defects.get(Ident.numbered(Kind.DEFECT, 2025, 142))
    assert got.meets == ClassOfTrack.EXCEPTED
