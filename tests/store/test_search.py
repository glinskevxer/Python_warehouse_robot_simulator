"""One search across every register."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Kind
from spikemaul.store.records import Records, records_in_memory
from spikemaul.store.search import by_number, by_text, find
from tests.support.books import (
    a_crossing,
    a_defect,
    a_gang,
    a_person,
    a_segment,
    a_subdivision,
    a_turnout,
    an_order,
)


def records() -> Records:
    book = records_in_memory(date(2025, 1, 6))
    book.subdivisions.add(a_subdivision())
    book.segments.add(a_segment())
    book.turnouts.add(a_turnout(at="13.00"))
    book.crossings.add(a_crossing(at="13.50"))
    book.people.add(a_person())
    book.people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    book.gangs.add(a_gang())
    book.defects.add(a_defect())
    book.orders.add(an_order())
    return book


def test_a_number_finds_the_record_whatever_kind_it_is() -> None:
    hits = find(records(), "SO-2025-0031")
    assert [one.kind for one in hits] == [Kind.ORDER]
    assert "13.00 to 13.60" in hits[0].says


def test_part_of_a_number_finds_everything_that_carries_it() -> None:
    hits = by_number(records(), "0031")
    assert len(hits) == 1
    assert hits[0].kind is Kind.ORDER


def test_a_number_of_one_kind_does_not_find_another() -> None:
    assert by_number(records(), "SG-014")[0].kind is Kind.SEGMENT
    assert len(by_number(records(), "SG-014")) == 1


def test_a_name_finds_the_person_who_has_it() -> None:
    hits = by_text(records(), "stivers")
    assert [one.kind for one in hits] == [Kind.PERSON]


def test_a_road_name_finds_the_crossing() -> None:
    hits = by_text(records(), "county road")
    assert [one.kind for one in hits] == [Kind.CROSSING]


def test_what_a_turnout_leads_to_is_searched() -> None:
    hits = by_text(records(), "bartels")
    assert [one.kind for one in hits] == [Kind.TURNOUT]


def test_a_gang_is_found_by_its_name_or_where_it_ties_up() -> None:
    assert by_text(records(), "section 2")[0].kind is Kind.GANG
    assert by_text(records(), "alden")[0].kind is Kind.GANG


def test_a_reading_written_on_a_card_is_searched() -> None:
    hits = by_text(records(), "57 7/8")
    assert [one.kind for one in hits] == [Kind.DEFECT]


def test_nothing_that_matches_gives_nothing() -> None:
    assert find(records(), "zzz") == []


def test_a_record_found_twice_is_listed_once() -> None:
    hits = find(records(), "PLAINS")
    kinds = [one.kind for one in hits]
    assert kinds.count(Kind.SUBDIVISION) == 1


def test_a_hit_says_which_kind_of_record_it_is() -> None:
    hits = find(records(), "SO-2025-0031")
    assert hits[0].describe().startswith("slow order")
