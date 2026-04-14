"""Opening a book, and the schema version written inside it."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from spikemaul.errors import BookError
from spikemaul.store.book import Book, is_open, new_book, open_book
from spikemaul.store.migrations import (
    MIGRATIONS,
    applied,
    migrate,
    pending,
    require_current,
    version,
)

ON = date(2025, 4, 21)


def test_a_book_that_is_not_there_is_not_quietly_created() -> None:
    with pytest.raises(BookError, match="there is no book at"):
        open_book("/tmp/no-such-spikemaul-book.sqlite3")


def test_a_book_is_made_where_the_caller_asks_for_one(tmp_path: Path) -> None:
    where = tmp_path / "plains.sqlite3"
    with open_book(where, create=True) as book:
        assert book.path == str(where)
    assert where.exists()


def test_a_directory_is_not_a_book(tmp_path: Path) -> None:
    with pytest.raises(BookError, match="is a directory"):
        open_book(tmp_path, create=True)


def test_a_new_book_is_at_schema_zero_and_has_nothing_in_it() -> None:
    with new_book() as book:
        migrate(book, ON)
        assert version(book) == len(MIGRATIONS)


def test_migrating_twice_runs_nothing_the_second_time() -> None:
    with new_book() as book:
        first = migrate(book, ON)
        assert [one.number for one in first] == [one.number for one in MIGRATIONS]
        assert migrate(book, ON) == []
        assert pending(book) == []


def test_the_book_says_which_migrations_it_has_run() -> None:
    with new_book() as book:
        migrate(book, ON)
        assert applied(book) == [one.number for one in MIGRATIONS]


def test_the_tables_are_there_after_migrating() -> None:
    with new_book() as book:
        migrate(book, ON)
        assert "subdivisions" in book.tables
        assert "equations" in book.tables
        assert "schema_migrations" in book.tables


def test_a_book_behind_this_package_is_refused() -> None:
    with new_book() as book:
        migrate(book, ON)
        book.execute("DELETE FROM schema_migrations WHERE number = ?", (len(MIGRATIONS),))
        with pytest.raises(BookError, match="wants"):
            require_current(book)


def test_a_book_newer_than_this_package_is_refused() -> None:
    with new_book() as book:
        migrate(book, ON)
        book.execute(
            "INSERT INTO schema_migrations (number, name, applied_on) VALUES (?, ?, ?)",
            (999, "from the future", ON.isoformat()),
        )
        with pytest.raises(BookError, match="newer than this package"):
            require_current(book)


def test_a_current_book_is_accepted() -> None:
    with new_book() as book:
        migrate(book, ON)
        require_current(book)


def test_a_bad_statement_comes_back_as_a_book_error() -> None:
    with new_book() as book, pytest.raises(BookError, match="no such table"):
        book.query("SELECT * FROM nothing_here")


def write_two_rows_one_of_which_is_wrong(book: Book) -> None:
    with book.writing():
        book.execute(
            "INSERT INTO subdivisions (ident, name, begin_post, end_post) VALUES (?,?,?,?)",
            ("SD-PLAINS", "Plains", 0, 12000),
        )
        book.execute("INSERT INTO subdivisions (ident) VALUES (?)", ("SD-PLAINS",))


def test_a_failed_transaction_leaves_nothing_behind() -> None:
    with new_book() as book:
        migrate(book, ON)
        with pytest.raises(BookError):
            write_two_rows_one_of_which_is_wrong(book)
        assert book.query("SELECT * FROM subdivisions") == []


def test_the_integrity_checks_pass_on_a_fresh_book() -> None:
    with new_book() as book:
        migrate(book, ON)
        assert book.check_integrity() == []
        assert book.foreign_key_problems() == []


def test_a_row_pointing_at_nothing_is_refused() -> None:
    with new_book() as book:
        migrate(book, ON)
        with pytest.raises(BookError, match="FOREIGN KEY"):
            book.execute(
                "INSERT INTO equations (subdivision, ordinal, back_post, ahead_post) "
                "VALUES (?,?,?,?)",
                ("SD-NOWHERE", 1, 6140, 6115),
            )


def test_a_book_can_be_closed_twice() -> None:
    book = new_book()
    book.close()
    book.close()


def test_the_connection_is_the_only_thing_touching_sqlite() -> None:
    with new_book() as book:
        assert isinstance(book, Book)
        assert isinstance(book.connection, sqlite3.Connection)


def test_a_book_says_whether_it_is_still_open() -> None:
    book = new_book()
    assert is_open(book)
    book.close()
    assert not is_open(book)
