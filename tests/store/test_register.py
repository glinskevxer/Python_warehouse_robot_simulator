"""What every register does the same way, tested through one of them."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.turnouts import Turnouts
from tests.support.books import a_book, a_subdivision, a_turnout


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
