"""The audit page: holes in the book rather than problems on the railroad."""

from __future__ import annotations

from datetime import date

from spikemaul.cwr.neutral import Destress
from spikemaul.model.ids import Ident, Kind
from spikemaul.report.audit import (
    audit_page,
    cards_off_the_line,
    cards_with_no_work,
    curves_off_the_line,
    holes,
    orders_without_a_card,
    unsegmented,
    welded_without_a_neutral,
)
from spikemaul.report.layout import render
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.span import Span
from spikemaul.units.temperature import Temperature
from tests.support.books import (
    a_curve,
    a_defect,
    a_person,
    a_segment,
    a_subdivision,
    a_work_order,
    an_order,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 20)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.people.add(a_person())
    book.people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    return book


def whole_subdivision(book: Records) -> None:
    book.segments.add(a_segment(number="014", span="0.00-61.40"))
    book.segments.add(a_segment(number="015", span="61.40-120.00"))


def test_a_subdivision_with_no_segments_is_all_hole() -> None:
    book = records()
    found = unsegmented(book, PLAINS)
    assert len(found) == 1
    assert "no segment covers it" in found[0].says


def test_a_subdivision_covered_end_to_end_has_no_gap() -> None:
    book = records()
    whole_subdivision(book)
    assert unsegmented(book, PLAINS) == []


def test_a_card_off_the_end_of_every_segment_is_a_hole() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00"))
    book.defects.add(a_defect(at="40.00"))
    found = cards_off_the_line(book, PLAINS)
    assert "is on no segment" in found[0].says


def test_a_curve_on_no_segment_is_a_hole() -> None:
    book = records()
    book.curves.add(a_curve(body="30.10-30.40"))
    assert curves_off_the_line(book, PLAINS) != []


def test_welded_rail_with_no_destress_entry_is_a_hole() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00", welded=True))
    found = welded_without_a_neutral(book, PLAINS, ON)
    assert "has no destress entry" in found[0].says


def test_welded_rail_with_an_entry_is_not_a_hole() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00", welded=True))
    book.destress.add(
        Destress(
            subdivision=PLAINS,
            span=Span.parse("12.00-14.00"),
            on=date(2025, 4, 20),
            neutral=Temperature(95),
            by=Ident.named(Kind.PERSON, "DKEHOE"),
        )
    )
    assert welded_without_a_neutral(book, PLAINS, ON) == []


def test_an_open_card_with_no_work_order_is_a_hole() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00"))
    book.defects.add(a_defect())
    assert cards_with_no_work(book, PLAINS) != []


def test_a_card_with_work_raised_against_it_is_not_a_hole() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00"))
    book.defects.add(a_defect())
    order = a_work_order()
    book.work.add(
        type(order)(
            **{
                **order.__dict__,
                "defect": Ident.numbered(Kind.DEFECT, 2025, 142),
            }
        )
    )
    assert cards_with_no_work(book, PLAINS) == []


def test_a_track_condition_order_with_no_card_behind_it_is_a_hole() -> None:
    book = records()
    whole_subdivision(book)
    book.orders.add(an_order())
    found = orders_without_a_card(book, PLAINS, ON)
    assert "no card behind it" in found[0].says


def test_the_page_says_how_many_holes_and_what_sqlite_thinks() -> None:
    book = records()
    whole_subdivision(book)
    text = render(audit_page(book, PLAINS, ON))
    assert "0 holes in the book" in text
    assert "the book covers the whole subdivision" in text
    assert "sqlite is happy with the file" in text


def test_the_page_lists_every_kind_of_hole_it_found() -> None:
    book = records()
    book.segments.add(a_segment(number="014", span="12.00-14.00", welded=True))
    book.defects.add(a_defect(at="40.00"))
    found = holes(book, PLAINS, ON)
    assert {one.kind for one in found} == {"track", "defect", "segment"}
    text = render(audit_page(book, PLAINS, ON))
    assert "records audit" in text
