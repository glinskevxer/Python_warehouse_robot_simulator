"""The rail page."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.model.side import Hand
from spikemaul.rail.wear import WearReading
from spikemaul.report.layout import render
from spikemaul.report.rails import rail_page, wear_table, worn_out
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.rails import FlawTest
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.tonnage import Tonnage
from tests.support.books import a_person, a_segment, a_subdivision, an_inspection

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 9, 1)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-16.00"))
    book.people.add(a_person())
    return book


def reading(post: str = "13.20", vertical: str = "1/4", on: date = date(2025, 4, 1)) -> WearReading:
    return WearReading(
        at=Milepost.parse(post),
        hand=Hand.LEFT,
        rail_section="115 RE",
        vertical=Inches.parse(vertical),
        gauge_face=Inches.parse("1/4"),
        measured_on=on,
    )


def test_a_subdivision_with_no_readings_says_so() -> None:
    text = render(rail_page(records(), PLAINS, ON))
    assert "no rail has been measured" in text
    assert "0 rails measured" in text


def test_a_reading_shows_with_what_it_holds() -> None:
    book = records()
    book.wear.add(reading(), PLAINS)
    text = render(rail_page(book, PLAINS, ON))
    assert "13.20" in text
    assert "class 5" in text
    assert "1 rail measured" in text


def test_rail_that_holds_nothing_is_counted_at_the_top() -> None:
    book = records()
    book.wear.add(reading(vertical="1"), PLAINS)
    text = render(rail_page(book, PLAINS, ON))
    assert "1 rail holding no class" in text
    assert "nothing" in text


def test_the_worst_rail_is_listed_first() -> None:
    book = records()
    book.wear.add(reading(post="13.20"), PLAINS)
    book.wear.add(reading(post="14.00", vertical="9/16"), PLAINS)
    text = render(rail_page(book, PLAINS, ON))
    assert text.index("14.00") < text.index("13.20")


def test_a_reading_below_the_class_is_marked_when_one_is_given() -> None:
    table = wear_table([reading(vertical="9/16")], ClassOfTrack.FOUR)
    assert any("below the class" in row for row in table.lines())


def test_the_rail_that_holds_nothing_is_found() -> None:
    assert worn_out([reading()]) == []
    assert len(worn_out([reading(vertical="1")])) == 1


def test_a_segment_nobody_has_tested_reads_never() -> None:
    text = render(rail_page(records(), PLAINS, ON))
    assert "never" in text
    assert "due" in text


def test_a_segment_that_has_been_tested_reads_in_cycle() -> None:
    book = records()
    number = Ident.numbered(Kind.INSPECTION, 2025, 70)
    book.inspections.add(
        an_inspection(
            sequence=70,
            on=date(2025, 8, 2),
            span="12.00-16.00",
            method=Method.FLAW_DETECTOR,
            scope=Scope.RAIL_FLAW,
        )
    )
    book.flaw_tests.add(
        FlawTest(number, PLAINS, Span.parse("12.00-16.00"), date(2025, 8, 2), Tonnage.of(124))
    )
    text = render(rail_page(book, PLAINS, ON))
    assert "in cycle" in text
    assert "2025-08-02" in text
