"""Writing the book out as csv."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import BookError
from spikemaul.store.export import tables_of, write_all, write_table
from spikemaul.store.records import Records, records_in_memory
from tests.support.books import a_segment, a_subdivision

ON = date(2025, 6, 1)


def a_book() -> Records:
    records = records_in_memory(ON)
    records.subdivisions.add(a_subdivision())
    records.segments.add(a_segment())
    return records


def test_the_tables_are_asked_of_the_book_not_listed_here() -> None:
    records = a_book()
    found = tables_of(records.book)
    assert "segments" in found
    assert "schema_migrations" not in found


def test_a_table_goes_out_with_its_column_names_on_the_first_line(tmp_path: Path) -> None:
    records = a_book()
    written = write_table(records.book, "segments", tmp_path)
    assert written.rows == 1
    with written.where.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "ident"
    assert rows[1][0] == "SG-014"


def test_every_table_gets_a_file_even_the_empty_ones(tmp_path: Path) -> None:
    records = a_book()
    written = write_all(records.book, tmp_path)
    names = {one.where.name for one in written}
    assert "segments.csv" in names
    assert "defects.csv" in names
    assert all(one.where.exists() for one in written)


def test_an_empty_table_writes_only_its_heading(tmp_path: Path) -> None:
    records = a_book()
    write_all(records.book, tmp_path)
    text = (tmp_path / "defects.csv").read_text(encoding="utf-8")
    assert text.strip().count("\n") == 0
    assert "ident" in text


def test_writing_into_a_directory_that_already_holds_csv_is_refused(tmp_path: Path) -> None:
    records = a_book()
    write_all(records.book, tmp_path)
    with pytest.raises(BookError, match="empty it first"):
        write_all(records.book, tmp_path)


def test_the_directory_is_made_where_it_is_not_there(tmp_path: Path) -> None:
    records = a_book()
    into = tmp_path / "out" / "here"
    write_all(records.book, into)
    assert into.exists()


def test_a_written_table_says_how_many_rows_went(tmp_path: Path) -> None:
    records = a_book()
    written = write_table(records.book, "subdivisions", tmp_path)
    assert written.describe() == "subdivisions: 1 rows to subdivisions.csv"
