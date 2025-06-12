"""The slow order register, asked what is in force on a day."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason
from spikemaul.store.orders import Orders
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.units.span import Span
from tests.support.books import a_book, a_plain_subdivision, a_subdivision, an_order

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def register() -> Orders:
    book = a_book()
    subdivisions = Subdivisions(book)
    subdivisions.add(a_subdivision())
    subdivisions.add(a_plain_subdivision())
    return Orders(book)


def test_an_order_comes_back_the_way_it_went_in() -> None:
    orders = register()
    orders.add(an_order())
    assert orders.get(Ident.numbered(Kind.ORDER, 2025, 31)) == an_order()


def test_what_is_in_force_is_asked_about_a_day() -> None:
    orders = register()
    orders.add(an_order())
    orders.add(an_order(sequence=32, span="20.00-21.00", effective=date(2025, 6, 1)))
    assert [one.ident.sequence for one in orders.in_force(PLAINS, date(2025, 5, 10))] == [31]
    assert len(orders.in_force(PLAINS, date(2025, 6, 2))) == 2


def test_an_order_that_has_expired_is_not_in_force_but_is_still_in_the_book() -> None:
    orders = register()
    orders.add(an_order(expires=date(2025, 5, 10)))
    assert orders.in_force(PLAINS, date(2025, 5, 10)) != []
    assert orders.in_force(PLAINS, date(2025, 5, 11)) == []
    assert orders.count() == 1


def test_an_order_that_was_lifted_is_not_in_force_from_that_day() -> None:
    orders = register()
    orders.add(an_order())
    order = orders.get(Ident.numbered(Kind.ORDER, 2025, 31))
    orders.update(order.lifted(date(2025, 5, 8)))
    assert orders.in_force(PLAINS, date(2025, 5, 7)) != []
    assert orders.in_force(PLAINS, date(2025, 5, 8)) == []


def test_the_orders_over_a_stretch_are_the_ones_that_overlap_it() -> None:
    orders = register()
    orders.add(an_order())
    orders.add(an_order(sequence=32, span="20.00-21.00"))
    got = orders.covering(PLAINS, Span.parse("13.50-14.00"), date(2025, 5, 10))
    assert [one.ident.sequence for one in got] == [31]


def test_standing_orders_are_the_ones_with_no_end_date_left_on() -> None:
    orders = register()
    orders.add(an_order())
    orders.add(
        an_order(sequence=32, span="20.00-21.00", reason=Reason.HEAT, expires=date(2025, 5, 6))
    )
    assert [one.ident.sequence for one in orders.standing(PLAINS)] == [31]


def test_the_orders_raised_against_a_card_can_be_asked_for() -> None:
    orders = register()
    card = Ident.numbered(Kind.DEFECT, 2025, 142)
    orders.add(an_order())
    assert orders.for_defect(card) == []


def test_the_next_number_follows_the_highest_one_that_year() -> None:
    orders = register()
    assert orders.next_number(2025) == Ident.numbered(Kind.ORDER, 2025, 1)
    orders.add(an_order())
    assert orders.next_number(2025) == Ident.numbered(Kind.ORDER, 2025, 32)


def test_an_order_raised_in_error_can_be_taken_back() -> None:
    orders = register()
    orders.add(an_order())
    orders.remove(Ident.numbered(Kind.ORDER, 2025, 31))
    assert orders.count() == 0


def test_an_order_that_was_in_force_and_lifted_stays_in_the_book() -> None:
    orders = register()
    orders.add(an_order())
    order = orders.get(Ident.numbered(Kind.ORDER, 2025, 31))
    orders.update(order.lifted(date(2025, 5, 8)))
    with pytest.raises(RuleError, match="stays in the book"):
        orders.remove(Ident.numbered(Kind.ORDER, 2025, 31))


def test_an_order_on_another_subdivision_is_not_in_force_here() -> None:
    orders = register()
    orders.add(an_order(subdivision="RIVER"))
    assert orders.in_force(PLAINS, date(2025, 5, 10)) == []
