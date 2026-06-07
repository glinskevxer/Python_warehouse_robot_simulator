"""The compliance page, built segment by segment."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.report.compliance import compliance_page, standings_for
from spikemaul.report.layout import render
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.records import Records, records_in_memory
from tests.support.books import (
    a_person,
    a_segment,
    a_subdivision,
    a_turnout,
    an_inspection,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 20)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-14.00"))
    book.people.add(a_person())
    book.people.add(a_person(initials="JHOLT", name="J Holt", scopes=frozenset(), until=None))
    return book


def test_a_subdivision_with_one_segment_watches_one_cycle() -> None:
    got = standings_for(records(), PLAINS, ON)
    assert [one.scope for one in got] == [Scope.TRACK]


def test_joint_bars_are_only_watched_where_the_rail_is_welded() -> None:
    book = records()
    book.segments.add(a_segment(number="015", span="14.00-16.00", welded=True))
    got = standings_for(book, PLAINS, ON)
    assert [one.scope for one in got].count(Scope.JOINT_BARS) == 1


def test_turnouts_are_only_watched_where_there_are_turnouts() -> None:
    book = records()
    book.turnouts.add(a_turnout(at="13.00"))
    got = standings_for(book, PLAINS, ON)
    assert Scope.TURNOUTS in [one.scope for one in got]


def test_two_segments_at_different_classes_run_two_cycles() -> None:
    book = records()
    book.segments.add(a_segment(number="015", span="14.00-16.00", authorized=ClassOfTrack.FOUR))
    got = standings_for(book, PLAINS, ON)
    cycles = {one.frequency.max_gap_days for one in got}
    assert cycles == {7, 3}


def test_the_page_counts_the_cycles_and_the_late_ones() -> None:
    text = render(compliance_page(records(), PLAINS, ON))
    assert "1 cycle watched, 1 cycle late" in text
    assert "never" in text


def test_an_inspection_inside_the_cycle_shows_a_due_date() -> None:
    book = records()
    book.inspections.add(an_inspection(on=date(2025, 5, 19), span="12.00-14.00"))
    text = render(compliance_page(book, PLAINS, ON))
    assert "2025-05-26" in text
    assert "1 cycle watched, 0 cycles late" in text


def test_an_inspection_that_did_not_count_is_listed_with_who_did_it() -> None:
    book = records()
    book.inspections.add(an_inspection(on=date(2025, 5, 19), span="12.00-14.00", by="JHOLT"))
    text = render(compliance_page(book, PLAINS, ON))
    assert "did not count" in text
    assert "JHOLT" in text


def test_a_book_where_everything_counted_says_so() -> None:
    book = records()
    book.inspections.add(an_inspection(on=date(2025, 5, 19), span="12.00-14.00"))
    text = render(compliance_page(book, PLAINS, ON))
    assert "every inspection recorded counted towards its cycle" in text


def test_a_subdivision_with_no_segments_has_nothing_to_watch() -> None:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    text = render(compliance_page(book, PLAINS, ON))
    assert "nothing to watch" in text


def test_a_walking_inspection_of_turnouts_counts_for_that_scope_only() -> None:
    book = records()
    book.turnouts.add(a_turnout(at="13.00"))
    book.inspections.add(
        an_inspection(
            on=date(2025, 5, 19),
            span="12.00-14.00",
            scope=Scope.TURNOUTS,
            method=Method.WALKING,
        )
    )
    got = standings_for(book, PLAINS, ON)
    by_scope = {one.scope: one for one in got}
    assert not by_scope[Scope.TURNOUTS].is_late
    assert by_scope[Scope.TRACK].is_late


def test_the_page_says_what_lapses_inside_the_window() -> None:
    book = records()
    text = render(compliance_page(book, PLAINS, date(2025, 12, 1)))
    assert "designations" in text
    assert "30 days left" in text


def test_the_page_says_what_has_already_lapsed() -> None:
    book = records()
    text = render(compliance_page(book, PLAINS, date(2026, 6, 1)))
    assert "lapsed" in text


def test_the_page_names_a_scope_nobody_is_designated_for() -> None:
    book = records()
    text = render(compliance_page(book, PLAINS, date(2025, 5, 20)))
    assert "nobody is designated for joint bars" in text


def test_a_quiet_window_says_nothing_lapses() -> None:
    book = records()
    text = render(compliance_page(book, PLAINS, date(2025, 5, 20)))
    assert "nothing lapses inside the window" in text
