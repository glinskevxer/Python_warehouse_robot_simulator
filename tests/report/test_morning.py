"""The morning page, and the order its sections are in."""

from __future__ import annotations

from datetime import date

from spikemaul.model.defect import Condition
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope
from spikemaul.program.compliance import Standing, standing_for
from spikemaul.report.layout import render
from spikemaul.report.morning import morning_page
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.store.records import Records, records_in_memory
from spikemaul.units.span import Span
from tests.support.books import (
    a_defect,
    a_gang,
    a_person,
    a_segment,
    a_subdivision,
    a_work_order,
    an_inspection,
    an_order,
)

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
ON = date(2025, 5, 20)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment())
    book.people.add(a_person())
    book.people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    book.gangs.add(a_gang())
    return book


def page_text(book: Records, standings: list[Standing] | None = None) -> str:
    return render(morning_page(book, PLAINS, ON, standings))


def test_a_quiet_morning_says_so_in_every_section() -> None:
    text = page_text(records())
    assert "Plains morning page 2025-05-20" in text
    assert "nothing out of service" in text
    assert "no restrictions in force" in text
    assert "no open defects" in text
    assert "every cycle in date" in text
    assert "no work open" in text


def test_the_sections_come_in_the_order_the_questions_are_asked() -> None:
    text = page_text(records())
    assert text.index("out of service") < text.index("bulletin")
    assert text.index("bulletin") < text.index("open defects")
    assert text.index("open defects") < text.index("inspections")
    assert text.index("inspections") < text.index("work")


def test_an_out_of_service_card_is_at_the_top() -> None:
    book = records()
    book.defects.add(a_defect(condition=Condition.RAIL_BREAK, meets=None, reading="broken base"))
    text = page_text(book)
    assert "DF-2025-0142" in text
    assert text.index("DF-2025-0142") < text.index("open defects")


def test_the_bulletin_lists_the_orders_in_force() -> None:
    book = records()
    book.orders.add(an_order())
    text = page_text(book)
    assert "SO-2025-0031" in text
    assert "track condition" in text
    assert "removed" in text


def test_an_order_that_is_not_in_force_is_not_on_the_page() -> None:
    book = records()
    book.orders.add(an_order(effective=date(2025, 6, 1)))
    assert "SO-2025-0031" not in page_text(book)


def test_an_overdue_card_is_marked_and_sorts_first() -> None:
    book = records()
    book.defects.add(a_defect(found_on=date(2025, 4, 1), sequence=100))
    book.defects.add(a_defect(sequence=142, at="13.40", found_on=date(2025, 5, 19)))
    text = page_text(book)
    assert "overdue" in text
    assert text.index("DF-2025-0100") < text.index("DF-2025-0142")


def test_a_late_cycle_shows_how_late_it_is() -> None:
    book = records()
    standing = standing_for(
        span=Span.parse("12.00-14.00"),
        scope=Scope.TRACK,
        track_class=ClassOfTrack.THREE,
        kind=TrackKind.MAIN,
        inspections=[an_inspection(on=date(2025, 5, 1))],
        people={Ident.named(Kind.PERSON, "RSTIVERS"): a_person()},
        on=ON,
    )
    text = page_text(book, [standing])
    assert "12" in text
    assert "every cycle in date" not in text


def test_open_work_is_listed_with_its_gang() -> None:
    book = records()
    book.work.add(a_work_order(gang="SEC2"))
    text = page_text(book)
    assert "WO-2025-0088" in text
    assert "SEC2" in text
    assert "400 ties" in text


def test_the_page_ends_with_the_counts() -> None:
    book = records()
    book.orders.add(an_order())
    book.work.add(a_work_order())
    assert page_text(book).rstrip().endswith("1 order in force, 1 work order open")


def test_a_card_off_the_end_of_every_segment_is_marked_rather_than_left_off() -> None:
    book = records()
    book.defects.add(a_defect(at="40.00"))
    text = page_text(book)
    assert "DF-2025-0142" in text
    assert "no segment" in text
