"""The general track bulletin."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason
from spikemaul.orders.bulletin import build, changes_between
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from tests.support.books import an_order

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
RIVER = Ident.named(Kind.SUBDIVISION, "RIVER")
ON = date(2025, 5, 10)


def test_a_subdivision_with_nothing_on_it_says_so() -> None:
    got = build(PLAINS, ON, [])
    assert got.is_clear
    assert got.lines() == ["PLAINS track bulletin 2025-05-10", "no restrictions in force"]
    assert got.describe() == "PLAINS 2025-05-10, nothing in force"
    assert got.slowest_speed() is None


def test_only_the_orders_in_force_on_the_day_are_on_it() -> None:
    orders = [an_order(), an_order(sequence=32, effective=date(2025, 6, 1))]
    assert len(build(PLAINS, ON, orders).orders) == 1
    assert len(build(PLAINS, date(2025, 6, 2), orders).orders) == 2


def test_orders_on_another_subdivision_are_not_on_this_bulletin() -> None:
    orders = [an_order(subdivision="RIVER")]
    assert build(PLAINS, ON, orders).is_clear
    assert not build(RIVER, ON, orders).is_clear


def test_the_orders_print_in_milepost_order() -> None:
    orders = [
        an_order(sequence=33, span="20.00-21.00"),
        an_order(sequence=31, span="13.00-13.60"),
    ]
    got = build(PLAINS, ON, orders)
    assert [one.ident.sequence for one in got.orders] == [31, 33]


def test_two_orders_starting_at_the_same_place_print_the_slower_first() -> None:
    orders = [
        an_order(sequence=31, span="13.00-13.60", mph=25),
        an_order(sequence=32, span="13.00-14.00", mph=10),
    ]
    got = build(PLAINS, ON, orders)
    assert [one.speed.mph for one in got.orders] == [10, 25]


def test_the_orders_that_lapse_are_kept_separate_and_marked() -> None:
    orders = [
        an_order(),
        an_order(sequence=44, span="20.00-21.00", reason=Reason.HEAT, expires=ON),
    ]
    got = build(PLAINS, ON, orders)
    assert [one.ident.sequence for one in got.standing] == [31]
    assert [one.ident.sequence for one in got.lapsing] == [44]
    assert got.lines()[-1].endswith("(lapses)")


def test_the_restricted_miles_count_overlap_once() -> None:
    orders = [
        an_order(sequence=31, span="13.00-14.00"),
        an_order(sequence=32, span="13.50-15.00"),
    ]
    assert build(PLAINS, ON, orders).restricted_miles == 2.0


def test_the_slowest_speed_on_the_bulletin_is_the_lowest_order() -> None:
    orders = [an_order(mph=25), an_order(sequence=32, span="20.00-21.00", mph=10)]
    assert build(PLAINS, ON, orders).slowest_speed() == Speed(10)


def test_the_orders_over_a_stretch_can_be_asked_for() -> None:
    orders = [an_order(), an_order(sequence=32, span="20.00-21.00")]
    got = build(PLAINS, ON, orders)
    assert [one.ident.sequence for one in got.covering(Span.parse("13.20-13.30"))] == [31]


def test_the_summary_line_carries_the_counts() -> None:
    orders = [an_order()]
    assert build(PLAINS, ON, orders).describe() == (
        "PLAINS 2025-05-10, 1 orders, 0.6 miles, slowest 10 mph"
    )


def test_what_went_on_and_what_came_off_between_two_days() -> None:
    monday = build(PLAINS, ON, [an_order()])
    orders = [
        an_order().lifted(date(2025, 5, 11)),
        an_order(sequence=32, span="20.00-21.00", effective=date(2025, 5, 11)),
    ]
    tuesday = build(PLAINS, date(2025, 5, 11), orders)
    put_on, came_off = changes_between(monday, tuesday)
    assert [one.ident.sequence for one in put_on] == [32]
    assert [one.ident.sequence for one in came_off] == [31]


def test_two_identical_bulletins_have_no_changes_between_them() -> None:
    first = build(PLAINS, ON, [an_order()])
    second = build(PLAINS, ON, [an_order()])
    assert changes_between(first, second) == ([], [])
