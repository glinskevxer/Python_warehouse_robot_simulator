"""The gang's week sheet."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind
from spikemaul.report.layout import render
from spikemaul.report.week import needs_from, week_for, week_page
from spikemaul.store.records import Records, records_in_memory
from tests.support.books import a_gang, a_person, a_segment, a_subdivision, a_work_order

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
SEC2 = Ident.named(Kind.GANG, "SEC2")
MONDAY = date(2025, 6, 2)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-16.00"))
    book.people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    book.gangs.add(a_gang())
    return book


def test_the_orders_become_needs_in_the_order_they_arrive() -> None:
    got = needs_from([a_work_order(), a_work_order(sequence=89, span="14.00-14.60")])
    assert [one.because for one in got] == ["WO-2025-0088", "WO-2025-0089"]
    assert got[0].kind is WorkKind.TIE_RENEWAL


def test_a_week_fills_the_days_from_what_the_gang_has_open() -> None:
    book = records()
    book.work.add(a_work_order(quantity=400, gang="SEC2"))
    plan = week_for(book, PLAINS, SEC2, MONDAY)
    assert [len(one.tasks) for one in plan.days] == [1, 1, 1, 1, 0]


def test_a_gang_with_nothing_of_its_own_takes_what_is_open() -> None:
    book = records()
    book.work.add(a_work_order(quantity=120))
    plan = week_for(book, PLAINS, SEC2, MONDAY)
    assert plan.days[0].tasks


def test_the_sheet_prints_the_days_and_the_material() -> None:
    book = records()
    book.work.add(a_work_order(quantity=240, gang="SEC2"))
    text = render(week_page(book, PLAINS, SEC2, MONDAY))
    assert "Section 2 week of 2025-06-02" in text
    assert "4 men" in text
    assert "crossties" in text
    assert "tie plates" in text


def test_a_week_that_holds_everything_says_so() -> None:
    book = records()
    book.work.add(a_work_order(quantity=120, gang="SEC2"))
    text = render(week_page(book, PLAINS, SEC2, MONDAY))
    assert "everything open fits in the week" in text


def test_work_that_did_not_fit_is_named_with_what_it_would_take() -> None:
    book = records()
    book.work.add(a_work_order(quantity=2000, gang="SEC2"))
    text = render(week_page(book, PLAINS, SEC2, MONDAY, days=2))
    assert "did not fit" in text
    assert "gang days to clear it" in text


def test_a_gang_with_no_work_has_a_week_of_empty_days() -> None:
    book = records()
    text = render(week_page(book, PLAINS, SEC2, MONDAY))
    assert "nothing planned" in text
    assert "nothing to order" in text
