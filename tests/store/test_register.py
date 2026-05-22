"""What every register does the same way, tested through one of them."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, InputError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.crew import People
from spikemaul.store.defects import Defects
from spikemaul.store.orders import Orders
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.turnouts import Turnouts
from spikemaul.store.work import WorkOrders
from tests.support.books import (
    a_book,
    a_defect,
    a_person,
    a_subdivision,
    a_turnout,
)


def register() -> Turnouts:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    return Turnouts(book)


def test_a_register_names_the_record_the_way_the_office_does() -> None:
    turnouts = register()
    with pytest.raises(NotFoundError, match="no turnout TO-31 in the book"):
        turnouts.get(Ident.named(Kind.TURNOUT, "31"))
    turnouts.add(a_turnout())
    with pytest.raises(DuplicateError, match="turnout TO-31 is already in the book"):
        turnouts.add(a_turnout())


def test_a_record_survives_a_round_trip_through_the_columns() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    assert turnouts.get(Ident.named(Kind.TURNOUT, "31")) == a_turnout()


def test_an_update_writes_every_column_but_the_number() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    turnouts.update(a_turnout(size=15, at="19.00", leads_to="team track"))
    got = turnouts.get(Ident.named(Kind.TURNOUT, "31"))
    assert got.size == 15
    assert str(got.point_of_switch) == "19.00"
    assert got.leads_to == "team track"


def test_a_clause_the_register_wrote_comes_back_in_its_own_order() -> None:
    turnouts = register()
    turnouts.add(a_turnout(number="33", at="21.00"))
    turnouts.add(a_turnout())
    got = turnouts.where("size = ?", (10,), "point_of_switch DESC")
    assert [one.ident.tail for one in got] == ["33", "31"]
    assert turnouts.first("size = ?", (99,)) is None


def test_the_count_and_the_listing_agree() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    turnouts.add(a_turnout(number="33", at="21.00"))
    assert turnouts.count() == len(turnouts.all()) == 2


def test_a_register_not_numbered_by_year_has_no_sequence_to_issue() -> None:
    turnouts = register()
    with pytest.raises(InputError, match="not issued by sequence"):
        turnouts.next_number(2025)


def numbered_registers() -> list[tuple[str, Defects | Orders | WorkOrders]]:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    People(book).add(a_person())
    return [
        ("defect", Defects(book)),
        ("slow order", Orders(book)),
        ("work order", WorkOrders(book)),
    ]


def test_every_register_numbered_by_year_starts_at_one() -> None:
    for _, register in numbered_registers():
        assert register.next_number(2025).sequence == 1


def test_the_year_is_part_of_the_number_and_the_sequence_restarts() -> None:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    People(book).add(a_person())
    defects = Defects(book)
    defects.add(a_defect(sequence=7))
    assert defects.next_number(2025).sequence == 8
    assert defects.next_number(2026).sequence == 1
    assert str(defects.next_number(2026)) == "DF-2026-0001"


def test_a_gap_left_by_a_cancelled_record_is_not_filled_in() -> None:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    People(book).add(a_person())
    defects = Defects(book)
    defects.add(a_defect(sequence=1))
    defects.add(a_defect(sequence=3, at="14.00"))
    defects.remove(Ident.numbered(Kind.DEFECT, 2025, 3))
    assert defects.next_number(2025).sequence == 2


def test_one_register_does_not_take_a_number_from_another() -> None:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    People(book).add(a_person())
    Defects(book).add(a_defect(sequence=42))
    assert Orders(book).next_number(2025).sequence == 1
