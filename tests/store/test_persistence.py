"""What is written is still there after the book is closed.

Every other test in this suite reads back through the connection that wrote,
which is exactly the reading that cannot see an uncommitted write. These tests
close the book and open it again, which is what the roadmaster does every
morning.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import BookError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.migrations import MIGRATIONS
from spikemaul.store.records import Records, open_records, start_records
from tests.support.books import (
    a_curve,
    a_defect,
    a_gang,
    a_person,
    a_segment,
    a_subdivision,
    a_turnout,
    a_work_order,
    an_inspection,
    an_order,
)

ON = date(2025, 7, 8)


def a_book_on_disk(where: Path) -> None:
    records = start_records(where, ON)
    records.subdivisions.add(a_subdivision())
    records.segments.add(a_segment())
    records.curves.add(a_curve())
    records.turnouts.add(a_turnout())
    records.people.add(a_person())
    records.people.add(a_person(initials="DKEHOE", name="D Kehoe"))
    records.gangs.add(a_gang())
    records.inspections.add(an_inspection())
    records.defects.add(a_defect())
    records.orders.add(an_order())
    records.work.add(a_work_order())
    records.close()


def test_every_register_survives_the_book_being_closed(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    a_book_on_disk(where)

    again = open_records(where)
    assert again.segments.count() == 1
    assert again.curves.count() == 1
    assert again.turnouts.count() == 1
    assert again.inspections.count() == 1
    assert again.defects.count() == 1
    assert again.orders.count() == 1
    assert again.work.count() == 1
    assert again.gangs.count() == 1
    again.close()


def test_a_record_comes_back_field_for_field_from_a_reopened_book(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    a_book_on_disk(where)

    again = open_records(where)
    assert again.segments.get(Ident.named(Kind.SEGMENT, "014")) == a_segment()
    assert again.defects.get(Ident.numbered(Kind.DEFECT, 2025, 142)) == a_defect()
    again.close()


def test_an_update_survives_the_book_being_closed(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    a_book_on_disk(where)

    records = open_records(where)
    card = records.defects.get(Ident.numbered(Kind.DEFECT, 2025, 142))
    records.defects.update(card.repaired(date(2025, 7, 20)))
    records.close()

    again = open_records(where)
    assert again.defects.get(Ident.numbered(Kind.DEFECT, 2025, 142)).repaired_on == date(
        2025, 7, 20
    )
    again.close()


def test_a_removal_survives_the_book_being_closed(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    a_book_on_disk(where)

    records = open_records(where)
    records.turnouts.remove(Ident.named(Kind.TURNOUT, "31"))
    records.close()

    again = open_records(where)
    assert again.turnouts.count() == 0
    again.close()


def test_a_book_behind_the_package_is_refused_on_the_way_in(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    records = start_records(where, ON)
    records.book.execute("DELETE FROM schema_migrations WHERE number = ?", (len(MIGRATIONS),))
    records.close()
    with pytest.raises(BookError, match="wants"):
        open_records(where)


def write_a_good_row_then_a_bad_one(records: Records) -> None:
    with records.book.writing():
        records.book.execute(
            "INSERT INTO segments (ident, subdivision, begin_post, end_post, kind, "
            "authorized, rail_section, rail_laid) VALUES (?,?,?,?,?,?,?,?)",
            ("SG-090", "SD-PLAINS", 100, 200, "main", 3, "115 RE", "1998-06-01"),
        )
        records.book.execute("INSERT INTO segments (ident) VALUES (?)", ("SG-091",))


def test_a_transaction_that_fails_leaves_nothing_behind_after_a_reopen(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    records = start_records(where, ON)
    records.subdivisions.add(a_subdivision())
    with pytest.raises(BookError):
        write_a_good_row_then_a_bad_one(records)
    records.close()

    again = open_records(where)
    assert again.segments.count() == 0
    again.close()
