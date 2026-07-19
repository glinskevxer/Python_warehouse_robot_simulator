"""Everything the book knows at one milepost."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.report.layout import render
from spikemaul.report.place import around, place_page
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.milepost import Milepost
from tests.support.books import (
    a_bridge,
    a_crossing,
    a_curve,
    a_defect,
    a_person,
    a_segment,
    a_subdivision,
    a_turnout,
    an_order,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 20)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment(number="014", span="12.00-16.00"))
    book.people.add(a_person())
    return book


def text_at(book: Records, post: str = "13.22") -> str:
    return render(place_page(book, PLAINS, Milepost.parse(post), ON))


def test_the_stretch_asked_about_is_a_hundredth_either_side() -> None:
    got = around(Milepost.parse("13.20"))
    assert str(got.begin) == "13.19"
    assert str(got.end) == "13.22"
    assert str(around(Milepost.parse("0.00")).begin) == "0.00"


def test_a_plain_milepost_says_the_segment_and_the_speed() -> None:
    text = text_at(records())
    assert "SG-014" in text
    assert "timetable speed 40 mph" in text
    assert "tangent track" in text
    assert "no open cards here" in text


def test_a_milepost_with_no_segment_says_so() -> None:
    text = text_at(records(), post="40.00")
    assert "no segment covers this milepost" in text


def test_a_milepost_in_a_curve_says_the_curve_speed() -> None:
    book = records()
    book.curves.add(a_curve(body="13.10-13.40", elevation="2", spirals=200))
    text = text_at(book)
    assert "CV-118" in text
    assert "curve speed 48 mph" in text


def test_a_milepost_in_a_spiral_says_which_part_of_the_curve_it_is() -> None:
    book = records()
    book.curves.add(a_curve(body="13.10-13.40", elevation="2", spirals=200))
    assert "in a spiral" in text_at(book, post="13.07")


def test_what_is_standing_at_the_milepost_is_listed() -> None:
    book = records()
    book.turnouts.add(a_turnout(at="13.22"))
    book.crossings.add(a_crossing(at="13.22"))
    book.bridges.add(a_bridge(at="13.22"))
    text = text_at(book)
    assert "TO-31" in text
    assert "XG-244" in text
    assert "BR-77" in text


def test_plain_track_says_there_is_nothing_recorded() -> None:
    assert "plain track" in text_at(records())


def test_an_open_card_is_listed_with_what_the_rule_requires() -> None:
    book = records()
    book.defects.add(a_defect(at="13.22"))
    text = text_at(book)
    assert "DF-2025-0142" in text
    assert "hold at class 1" in text


def test_the_speed_says_what_sets_it() -> None:
    book = records()
    text = text_at(book)
    assert "40 mph because of the class" in text


def test_an_order_in_force_takes_the_speed_and_is_listed() -> None:
    book = records()
    book.orders.add(an_order(span="13.00-13.60"))
    text = text_at(book)
    assert "10 mph because of the slow order" in text
    assert "SO-2025-0031" in text


def test_a_milepost_with_no_records_at_all_says_nothing_sets_a_speed() -> None:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    text = text_at(book, post="40.00")
    assert "nothing on record sets a speed here" in text


def test_the_class_the_segment_holds_decides_the_remedy_printed() -> None:
    book = records()
    book.segments.remove(Ident.named(Kind.SEGMENT, "014"))
    book.segments.add(a_segment(number="015", span="12.00-16.00", authorized=ClassOfTrack.ONE))
    book.defects.add(a_defect(at="13.22"))
    text = text_at(book)
    assert "no action, the condition meets the class" in text
