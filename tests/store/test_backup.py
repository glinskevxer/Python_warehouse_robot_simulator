"""Copying the book through sqlite."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import BookError
from spikemaul.store.backup import named_for, restore, take
from spikemaul.store.records import open_records, start_records
from tests.support.books import a_segment, a_subdivision

ON = date(2025, 6, 1)


def a_book_on_disk(where: Path) -> Path:
    book = where / "plains.sqlite3"
    records = start_records(book, ON)
    records.subdivisions.add(a_subdivision())
    records.segments.add(a_segment())
    records.close()
    return book


def test_a_backup_is_named_for_the_day_it_was_taken() -> None:
    assert named_for(Path("/tmp/plains.sqlite3"), ON).name == "plains-2025-06-01.sqlite3"


def test_a_copy_holds_what_the_book_held(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    taken = take(records.book, named_for(book, ON))
    records.close()

    assert taken.is_sound
    assert taken.tables > 10
    again = open_records(taken.where)
    assert again.segments.count() == 1
    again.close()


def test_a_copy_says_it_reads_clean(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    taken = take(records.book, named_for(book, ON))
    records.close()
    assert "reads clean" in taken.describe()


def test_a_copy_is_taken_while_the_book_is_open(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    records.segments.add(a_segment(number="015", span="20.00-21.00"))
    taken = take(records.book, named_for(book, ON))
    records.close()

    again = open_records(taken.where)
    assert again.segments.count() == 2
    again.close()


def test_a_second_backup_on_the_same_day_is_refused(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    take(records.book, named_for(book, ON))
    with pytest.raises(BookError, match="already a backup at"):
        take(records.book, named_for(book, ON))
    records.close()


def test_a_backup_can_be_put_back_where_there_is_no_book(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    taken = take(records.book, named_for(book, ON))
    records.close()

    onto = tmp_path / "restored.sqlite3"
    assert restore(taken.where, onto) == onto
    again = open_records(onto)
    assert again.subdivisions.count() == 1
    again.close()


def test_restoring_over_a_book_that_is_there_is_refused(tmp_path: Path) -> None:
    book = a_book_on_disk(tmp_path)
    records = open_records(book)
    taken = take(records.book, named_for(book, ON))
    records.close()
    with pytest.raises(BookError, match="move it before restoring"):
        restore(taken.where, book)


def test_a_backup_that_is_not_there_cannot_be_restored(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="there is no backup at"):
        restore(tmp_path / "nothing.sqlite3", tmp_path / "onto.sqlite3")
