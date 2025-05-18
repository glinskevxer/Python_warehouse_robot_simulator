"""The turnout register, which answers in the order a foreman walks them."""

from __future__ import annotations

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.turnouts import Turnouts
from spikemaul.units.span import Span
from tests.support.books import a_book, a_plain_subdivision, a_subdivision, a_turnout

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def register() -> Turnouts:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Turnouts(book)


def test_a_turnout_comes_back_the_way_it_went_in() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    assert turnouts.get(Ident.named(Kind.TURNOUT, "31")) == a_turnout()


def test_the_same_turnout_twice_is_refused() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    with pytest.raises(DuplicateError, match="already in the book"):
        turnouts.add(a_turnout())


def test_a_turnout_that_is_not_there_is_not_invented() -> None:
    turnouts = register()
    with pytest.raises(NotFoundError, match="no turnout"):
        turnouts.get(Ident.named(Kind.TURNOUT, "31"))


def test_turnouts_come_back_in_milepost_order() -> None:
    turnouts = register()
    turnouts.add(a_turnout(number="34", at="24.10"))
    turnouts.add(a_turnout())
    turnouts.add(a_turnout(number="33", at="21.00"))
    assert [one.ident.tail for one in turnouts.on(PLAINS)] == ["31", "33", "34"]


def test_the_turnouts_inside_a_stretch_take_the_near_end_and_not_the_far_one() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    turnouts.add(a_turnout(number="33", at="21.00"))
    got = turnouts.within(PLAINS, Span.parse("18.60-21.00"))
    assert [one.ident.tail for one in got] == ["31"]


def test_a_turnout_on_another_subdivision_is_not_in_this_stretch() -> None:
    turnouts = register()
    turnouts.add(a_turnout(subdivision="RIVER"))
    assert turnouts.within(PLAINS, Span.parse("18.00-19.00")) == []
    assert turnouts.count() == 1


def test_every_turnout_comes_back_in_subdivision_and_milepost_order() -> None:
    turnouts = register()
    turnouts.add(a_turnout(number="80", subdivision="RIVER", at="4.00"))
    turnouts.add(a_turnout())
    assert [one.ident.tail for one in turnouts.all()] == ["31", "80"]


def test_a_turnout_can_be_written_over() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    turnouts.update(a_turnout(size=15, leads_to="house track"))
    got = turnouts.get(Ident.named(Kind.TURNOUT, "31"))
    assert got.size == 15
    assert got.leads_to == "house track"


def test_updating_or_removing_something_that_is_not_there_is_refused() -> None:
    turnouts = register()
    with pytest.raises(NotFoundError, match="no turnout"):
        turnouts.update(a_turnout())
    with pytest.raises(NotFoundError, match="no turnout"):
        turnouts.remove(Ident.named(Kind.TURNOUT, "31"))


def test_a_turnout_can_be_taken_out() -> None:
    turnouts = register()
    turnouts.add(a_turnout())
    turnouts.remove(Ident.named(Kind.TURNOUT, "31"))
    assert turnouts.count() == 0
