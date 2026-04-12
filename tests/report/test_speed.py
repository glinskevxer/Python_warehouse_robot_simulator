"""The speed profile page, built out of the book."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.report.layout import render
from spikemaul.report.speed import caps_for, profile_for, speed_page
from spikemaul.standards.classes import ClassOfTrack, Traffic
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from tests.support.books import a_curve, a_segment, a_subdivision, an_order

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 20)
OVER = Span.parse("12.00-16.00")


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-16.00", authorized=ClassOfTrack.FOUR))
    return book


def test_the_caps_come_off_every_register_that_holds_one() -> None:
    book = records()
    book.curves.add(a_curve(body="13.10-13.40", degrees=6, elevation="1"))
    book.orders.add(an_order())
    caps = caps_for(book, PLAINS, OVER, ON)
    assert {one.because for one in caps} == {"class", "curve", "slow order"}


def test_the_profile_takes_the_lowest_cap_at_each_foot() -> None:
    book = records()
    book.orders.add(an_order())
    pieces = profile_for(book, PLAINS, OVER, ON)
    assert [one.speed.mph for one in pieces] == [60, 10, 60]


def test_passenger_traffic_reads_the_other_column_of_the_class_table() -> None:
    book = records()
    pieces = profile_for(book, PLAINS, OVER, ON, Traffic.PASSENGER)
    assert pieces[0].speed == Speed(80)


def test_the_page_prints_the_profile_and_the_running_time() -> None:
    book = records()
    book.orders.add(an_order())
    text = render(speed_page(book, PLAINS, OVER, ON))
    assert "speed profile" in text
    assert "slow order" in text
    assert "minutes" in text


def test_the_page_prices_the_restrictions_when_given_a_timetable() -> None:
    book = records()
    book.orders.add(an_order())
    text = render(speed_page(book, PLAINS, OVER, ON, Speed(60)))
    assert "minutes lost against 60 mph" in text


def test_the_page_names_the_track_no_segment_covers() -> None:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    text = render(speed_page(book, PLAINS, OVER, ON))
    assert "no record covers any of this stretch" in text
    assert "has no segment recorded" in text
