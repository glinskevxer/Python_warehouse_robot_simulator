"""The exception log off one geometry run."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.model.reading import Run
from spikemaul.report.exceptions import assess_run, exception_page, worst_segment
from spikemaul.report.layout import render
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.measure import Inches
from tests.support.books import (
    a_curve,
    a_person,
    a_reading,
    a_segment,
    a_subdivision,
    an_inspection,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
RUN_ON = date(2025, 5, 6)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-13.00"))
    book.segments.add(a_segment(number="015", span="13.00-14.00", authorized=ClassOfTrack.FOUR))
    book.people.add(a_person())
    book.inspections.add(
        an_inspection(
            sequence=52,
            on=RUN_ON,
            span="12.00-14.00",
            method=Method.GEOMETRY_CAR,
            scope=Scope.TRACK,
        )
    )
    return book


def run(*readings: object) -> Run:
    return Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 52),
        subdivision=PLAINS,
        on=RUN_ON,
        readings=list(readings),  # type: ignore[arg-type]
    )


def clean_run() -> Run:
    return run(
        a_reading("12.00"),
        a_reading("12.50"),
        a_reading("13.10"),
        a_reading("13.50"),
    )


def test_a_run_is_read_against_each_segment_it_crosses() -> None:
    got = assess_run(records(), clean_run())
    assert [one.segment.ident.tail for one in got] == ["014", "015"]
    assert all(one.assessment.is_clear for one in got)


def test_a_segment_with_one_reading_on_it_is_left_out() -> None:
    short = run(a_reading("12.00"), a_reading("12.50"), a_reading("13.10"))
    got = assess_run(records(), short)
    assert [one.segment.ident.tail for one in got] == ["014"]


def test_the_same_reading_is_an_exception_on_one_segment_and_not_the_other() -> None:
    both = run(
        a_reading("12.00"),
        a_reading("12.50", gauge=Inches.parse("57 5/8")),
        a_reading("13.10", gauge=Inches.parse("57 5/8")),
        a_reading("13.50"),
    )
    got = assess_run(records(), both)
    assert got[0].findings == []
    assert [one.condition.value for one in got[1].findings] == ["gauge"]


def test_the_curve_register_decides_how_a_crosslevel_reading_is_read() -> None:
    book = records()
    book.curves.add(a_curve(body="12.40-12.60", elevation="2", spirals=0))
    curved = run(
        a_reading("12.00"),
        a_reading("12.50", crosslevel=Inches.parse("2")),
        a_reading("13.10"),
        a_reading("13.50"),
    )
    got = assess_run(book, curved)
    assert got[0].findings == []
    without = assess_run(records(), curved)
    assert [one.condition.value for one in without[0].findings] == ["crosslevel"]


def test_the_page_lists_the_exceptions_and_then_the_segments() -> None:
    book = records()
    bad = run(
        a_reading("12.00"),
        a_reading("12.50", gauge=Inches.parse("57 7/8")),
        a_reading("13.10"),
        a_reading("13.50"),
    )
    text = render(exception_page(book, bad))
    assert "Plains geometry exceptions 2025-05-06" in text
    assert "MP 12.50" in text
    assert text.index("exceptions") < text.index("by segment")
    assert "hold at class 1" in text


def test_a_clean_run_says_there_were_no_exceptions() -> None:
    text = render(exception_page(records(), clean_run()))
    assert "no exceptions" in text
    assert "SG-014" in text


def test_the_worst_segment_is_the_one_left_holding_least() -> None:
    book = records()
    bad = run(
        a_reading("12.00"),
        a_reading("12.50"),
        a_reading("13.10", gauge=Inches.parse("57 7/8")),
        a_reading("13.50"),
    )
    got = worst_segment(assess_run(book, bad))
    assert got is not None
    assert got.segment.ident.tail == "015"
    assert worst_segment([]) is None
