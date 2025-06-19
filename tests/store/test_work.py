"""The work order register, which answers a backlog and a plan separately."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind
from spikemaul.store.crew import Gangs, People
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.work import WorkOrders
from spikemaul.units.span import Span
from tests.support.books import (
    a_book,
    a_gang,
    a_person,
    a_plain_subdivision,
    a_subdivision,
    a_work_order,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
SEC2 = Ident.named(Kind.GANG, "SEC2")


def register() -> WorkOrders:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    people = People(book)
    people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    Gangs(book).add(a_gang())
    return WorkOrders(book)


def test_an_order_comes_back_the_way_it_went_in() -> None:
    work = register()
    work.add(a_work_order())
    assert work.get(Ident.numbered(Kind.WORK, 2025, 88)) == a_work_order()


def test_open_is_having_no_finished_date() -> None:
    work = register()
    work.add(a_work_order())
    order = work.get(Ident.numbered(Kind.WORK, 2025, 88))
    work.update(order.finished(date(2025, 6, 1), 380))
    assert work.open_on(PLAINS) == []
    assert work.get(Ident.numbered(Kind.WORK, 2025, 88)).shortfall == 20


def test_unassigned_is_a_different_question_to_open() -> None:
    work = register()
    work.add(a_work_order())
    work.add(a_work_order(sequence=89, span="20.00-21.00", gang="SEC2"))
    assert [one.ident.sequence for one in work.open_on(PLAINS)] == [88, 89]
    assert [one.ident.sequence for one in work.unassigned(PLAINS)] == [88]


def test_what_a_gang_has_open_is_its_plan() -> None:
    work = register()
    work.add(a_work_order(gang="SEC2"))
    work.add(a_work_order(sequence=89, span="20.00-21.00", gang="SEC2"))
    order = work.get(Ident.numbered(Kind.WORK, 2025, 89))
    work.update(order.finished(date(2025, 6, 1)))
    assert [one.ident.sequence for one in work.for_gang(SEC2)] == [88]


def test_overdue_is_open_and_past_the_date() -> None:
    work = register()
    work.add(a_work_order(due_on=date(2025, 6, 1)))
    work.add(a_work_order(sequence=89, span="20.00-21.00"))
    assert work.overdue(PLAINS, date(2025, 6, 1)) == []
    assert [one.ident.sequence for one in work.overdue(PLAINS, date(2025, 6, 2))] == [88]


def test_orders_over_a_stretch_include_the_finished_ones() -> None:
    work = register()
    work.add(a_work_order())
    order = work.get(Ident.numbered(Kind.WORK, 2025, 88))
    work.update(order.finished(date(2025, 6, 1)))
    got = work.within(PLAINS, Span.parse("13.50-14.00"))
    assert [one.ident.sequence for one in got] == [88]


def test_orders_can_be_asked_for_by_the_card_they_came_off() -> None:
    work = register()
    work.add(a_work_order())
    assert work.for_defect(Ident.numbered(Kind.DEFECT, 2025, 142)) == []


def test_the_next_number_follows_the_highest_one_that_year() -> None:
    work = register()
    assert work.next_number(2025) == Ident.numbered(Kind.WORK, 2025, 1)
    work.add(a_work_order())
    assert work.next_number(2025) == Ident.numbered(Kind.WORK, 2025, 89)


def test_the_quantity_keeps_the_unit_of_its_kind_through_the_book() -> None:
    work = register()
    work.add(a_work_order(kind=WorkKind.SURFACING, quantity=3200))
    got = work.get(Ident.numbered(Kind.WORK, 2025, 88))
    assert got.unit == "feet"


def test_an_order_that_is_not_there_is_not_invented() -> None:
    work = register()
    with pytest.raises(NotFoundError, match="no work order"):
        work.get(Ident.numbered(Kind.WORK, 2025, 88))
