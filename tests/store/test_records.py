"""One handle on all the registers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import BookError
from spikemaul.store.migrations import MIGRATIONS
from spikemaul.store.records import open_records, records_in_memory, start_records
from tests.support.books import a_person, a_subdivision

ON = date(2025, 7, 1)


def test_a_new_book_comes_up_with_the_schema_on_it(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    records = start_records(where, ON)
    assert records.schema == len(MIGRATIONS)
    assert records.is_empty()
    records.close()


def test_an_existing_book_is_opened_and_read(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    first = start_records(where, ON)
    first.subdivisions.add(a_subdivision())
    first.close()

    again = open_records(where)
    assert [one.code for one in again.subdivisions.all()] == ["PLAINS"]
    again.close()


def test_a_book_that_is_not_there_is_not_created_by_opening_it(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="there is no book at"):
        open_records(tmp_path / "nothing.sqlite3")


def test_every_register_is_built_and_usable() -> None:
    records = records_in_memory(ON)
    records.subdivisions.add(a_subdivision())
    records.people.add(a_person())
    counts = records.counts()
    assert counts["subdivisions"] == 1
    assert counts["people"] == 1
    assert counts["defects"] == 0
    assert not records.is_empty()


def test_the_counts_name_every_register_that_holds_records() -> None:
    records = records_in_memory(ON)
    assert set(records.counts()) == {
        "subdivisions",
        "segments",
        "curves",
        "turnouts",
        "crossings",
        "bridges",
        "inspections",
        "defects",
        "orders",
        "work orders",
        "people",
        "gangs",
        "tie surveys",
        "wear readings",
        "flaw tests",
        "destress entries",
    }


def test_starting_a_book_that_is_already_there_leaves_it_alone(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    first = start_records(where, ON)
    first.subdivisions.add(a_subdivision())
    first.close()
    again = start_records(where, ON)
    assert again.subdivisions.count() == 1
    again.close()
