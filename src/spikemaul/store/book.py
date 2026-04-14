"""The book itself: one sqlite file with the whole track department in it.

The file is the record. There is no server and there is nobody to ask, so the
things that would be somebody else's job somewhere else are this module's job
here: foreign keys on, one writer at a time, and a schema version written into
the file rather than assumed from the name of the program that opened it.

The connection runs in autocommit, so a single statement is committed when it
returns and a caller that wants several statements to land together says so
with :meth:`Book.writing`. The alternative, python's implicit transaction, is
what this started with, and it meant every register write sat uncommitted
until something else happened to commit. Every test passed, because a test
reads back through the same connection that wrote.

Opening a book that does not exist is an error unless the caller says to make
one. That is deliberate. A typo in a path that quietly creates an empty book
looks exactly like a book that lost everything, and the roadmaster finds out
by printing an empty bulletin.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from spikemaul.errors import BookError

MEMORY = ":memory:"
"""The path that means a book that is thrown away when it is closed."""


@dataclass
class Book:
    """An open book, and the only thing that touches sqlite."""

    connection: sqlite3.Connection
    path: str

    def close(self) -> None:
        """Close the file. Closing twice is not an error."""
        self.connection.close()

    def __enter__(self) -> Book:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def execute(self, sql: str, values: Sequence[Any] = ()) -> sqlite3.Cursor:
        """Run one statement, turning sqlite's complaints into ours."""
        try:
            return self.connection.execute(sql, values)
        except sqlite3.Error as exc:
            raise BookError(f"{exc} while running {sql.strip().splitlines()[0]}") from exc

    def query(self, sql: str, values: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Run one statement and read all of it, which is what registers want."""
        return list(self.execute(sql, values).fetchall())

    def one(self, sql: str, values: Sequence[Any] = ()) -> sqlite3.Row | None:
        """Run one statement and take the first row, or nothing."""
        found: sqlite3.Row | None = self.execute(sql, values).fetchone()
        return found

    @contextmanager
    def writing(self) -> Iterator[Book]:
        """A transaction that is committed on the way out or rolled back.

        Every register method that writes more than one row goes through here,
        because half a work order is worse than no work order. A single row
        write does not need it: the connection is in autocommit, so one
        statement is already one transaction.
        """
        self.execute("BEGIN IMMEDIATE")
        try:
            yield self
        except BaseException:
            self.connection.rollback()
            raise
        self.connection.commit()

    @property
    def tables(self) -> list[str]:
        """Every table in the book, in name order."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    def check_integrity(self) -> list[str]:
        """What sqlite says is wrong with the file, empty when nothing is."""
        rows = self.query("PRAGMA integrity_check")
        found = [str(row[0]) for row in rows]
        return [] if found == ["ok"] else found

    def foreign_key_problems(self) -> list[str]:
        """Rows pointing at records that are not there."""
        rows = self.query("PRAGMA foreign_key_check")
        return [f"{row[0]} row {row[1]} points at a missing {row[2]}" for row in rows]


def open_book(path: str | Path, create: bool = False) -> Book:
    """Open a book, or make one where the caller has asked for that."""
    where = str(path)
    if where != MEMORY:
        exists = Path(where).exists()
        if not exists and not create:
            raise BookError(f"there is no book at {where}")
        if exists and Path(where).is_dir():
            raise BookError(f"{where} is a directory, not a book")
    connection = sqlite3.connect(where, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return Book(connection=connection, path=where)


def new_book() -> Book:
    """A book in memory, which the tests and the dry runs use."""
    return open_book(MEMORY, create=True)


def is_open(book: Book) -> bool:
    """Whether a book still has its connection, which a closed one does not."""
    try:
        book.connection.execute("SELECT 1")
    except Exception:  # noqa: BLE001
        return False
    return True
